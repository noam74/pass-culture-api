from contextlib import contextmanager
from dataclasses import asdict
from datetime import date
from datetime import datetime
from datetime import timedelta
from decimal import Decimal
from enum import Enum
import logging
import random
import secrets
import typing
from typing import Optional
from typing import Tuple
from typing import Union

from flask import current_app as app
from google.cloud.storage.blob import Blob
from jwt import DecodeError
from jwt import ExpiredSignatureError
from jwt import InvalidSignatureError
from jwt import InvalidTokenError
from redis import Redis

# TODO (viconnex): fix circular import of pcapi/models/__init__.py
from pcapi import models  # pylint: disable=unused-import
from pcapi import settings
from pcapi.connectors.beneficiaries.id_check_middleware import ask_for_identity_document_verification
from pcapi.core import mails
from pcapi.core.bookings.conf import LIMIT_CONFIGURATIONS
import pcapi.core.bookings.repository as bookings_repository
import pcapi.core.fraud.api as fraud_api
import pcapi.core.fraud.models as fraud_models
import pcapi.core.payments.api as payment_api
from pcapi.core.users.external import update_external_user
from pcapi.core.users.models import Credit
from pcapi.core.users.models import DomainsCredit
from pcapi.core.users.models import NotificationSubscriptions
from pcapi.core.users.models import PhoneValidationStatusType
from pcapi.core.users.models import Token
from pcapi.core.users.models import TokenType
from pcapi.core.users.models import User
from pcapi.core.users.models import VOID_PUBLIC_NAME
from pcapi.core.users.repository import does_validated_phone_exist
from pcapi.core.users.repository import get_and_lock_user
from pcapi.core.users.repository import get_beneficiary_import_for_beneficiary
from pcapi.core.users.utils import decode_jwt_token
from pcapi.core.users.utils import delete_object
from pcapi.core.users.utils import encode_jwt_payload
from pcapi.core.users.utils import get_object
from pcapi.core.users.utils import sanitize_email
from pcapi.core.users.utils import store_object
from pcapi.domain import user_emails
from pcapi.domain.beneficiary_pre_subscription.model import BeneficiaryPreSubscription
from pcapi.domain.password import random_hashed_password
from pcapi.domain.postal_code.postal_code import PostalCode
from pcapi.domain.user_activation import create_beneficiary_from_application
from pcapi.emails.beneficiary_email_change import build_beneficiary_confirmation_email_change_data
from pcapi.emails.beneficiary_email_change import build_beneficiary_information_email_change_data
from pcapi.models import BeneficiaryImport
from pcapi.models import Booking
from pcapi.models import ImportStatus
from pcapi.models.db import db
from pcapi.models.feature import FeatureToggle
from pcapi.models.user_offerer import UserOfferer
from pcapi.models.user_session import UserSession
from pcapi.notifications.sms import send_transactional_sms
from pcapi.notifications.sms.sending_limit import is_SMS_sending_allowed
from pcapi.notifications.sms.sending_limit import update_sent_SMS_counter
from pcapi.repository import repository
from pcapi.repository import transaction
from pcapi.repository.user_queries import find_user_by_email
from pcapi.routes.serialization.users import ProUserCreationBodyModel
from pcapi.tasks.account import VerifyIdentityDocumentRequest
from pcapi.tasks.account import verify_identity_document
from pcapi.utils import phone_number as phone_number_utils
from pcapi.utils.token import random_token
from pcapi.utils.urls import get_webapp_url
from pcapi.workers.apps_flyer_job import log_user_becomes_beneficiary_event_job


logger = logging.getLogger(__name__)

from pcapi.utils.mailing import MailServiceException

from . import constants
from . import exceptions
from ..offerers.api import create_digital_venue
from ..offerers.models import Offerer


UNCHANGED = object()
logger = logging.getLogger(__name__)


class BeneficiaryValidationStep(Enum):
    PHONE_VALIDATION = "phone-validation"
    ID_CHECK = "id-check"


def create_email_validation_token(user: User) -> Token:
    return generate_and_save_token(
        user, TokenType.EMAIL_VALIDATION, life_time=constants.EMAIL_VALIDATION_TOKEN_LIFE_TIME
    )


def create_reset_password_token(user: User, token_life_time: timedelta = None) -> Token:
    return generate_and_save_token(
        user, TokenType.RESET_PASSWORD, life_time=token_life_time or constants.RESET_PASSWORD_TOKEN_LIFE_TIME
    )


def count_existing_id_check_tokens(user: User) -> int:
    return (
        Token.query.filter(Token.userId == user.id)
        .filter_by(type=TokenType.ID_CHECK)
        .filter(Token.expirationDate > datetime.now())
        .count()
    )


def create_id_check_token(user: User) -> Optional[Token]:
    if not user.is_eligible or user.isBeneficiary:
        return None

    alive_token_count = count_existing_id_check_tokens(user)
    if alive_token_count >= settings.ID_CHECK_MAX_ALIVE_TOKEN:
        raise exceptions.IdCheckTokenLimitReached(alive_token_count)

    if user.hasCompletedIdCheck:
        raise exceptions.IdCheckAlreadyCompleted()

    return generate_and_save_token(user, TokenType.ID_CHECK, constants.ID_CHECK_TOKEN_LIFE_TIME)


def create_phone_validation_token(user: User) -> Optional[Token]:
    random_code = "".join([str(random.randint(0, 9)) for _ in range(0, 6)])

    return generate_and_save_token(
        user, TokenType.PHONE_VALIDATION, constants.PHONE_VALIDATION_TOKEN_LIFE_TIME, token_value=random_code
    )


def generate_and_save_token(
    user: User, token_type: TokenType, life_time: Optional[timedelta] = None, token_value: Optional[str] = None
) -> Token:
    assert token_type.name in TokenType.__members__, "Only registered token types are allowed"

    expiration_date = datetime.now() + life_time if life_time else None
    token_value = token_value or secrets.token_urlsafe(32)

    token = Token(user=user, value=token_value, type=token_type, expirationDate=expiration_date)
    repository.save(token)

    return token


def delete_expired_tokens() -> None:
    Token.query.filter(Token.expirationDate < datetime.now()).delete()


def delete_all_users_tokens(user: User) -> None:
    Token.query.filter(Token.user == user).delete()


def create_account(
    email: str,
    password: str,
    birthdate: date,
    marketing_email_subscription: bool = False,
    is_email_validated: bool = False,
    send_activation_mail: bool = True,
    remote_updates: bool = True,
    postal_code: str = None,
    phone_number: str = None,
    apps_flyer_user_id: str = None,
    apps_flyer_platform: str = None,
) -> User:
    email = sanitize_email(email)
    if find_user_by_email(email):
        raise exceptions.UserAlreadyExistsException()

    departement_code = PostalCode(postal_code).get_departement_code() if postal_code else None

    user = User(
        email=email,
        dateOfBirth=datetime.combine(birthdate, datetime.min.time()),
        isEmailValidated=is_email_validated,
        publicName=VOID_PUBLIC_NAME,  # Required because model validation requires 3+ chars
        hasSeenTutorials=False,
        notificationSubscriptions=asdict(NotificationSubscriptions(marketing_email=marketing_email_subscription)),
        postalCode=postal_code,
        departementCode=departement_code,
        phoneNumber=phone_number,
        lastConnectionDate=datetime.now(),
    )

    if not user.age or user.age < constants.ACCOUNT_CREATION_MINIMUM_AGE:
        raise exceptions.UnderAgeUserException()

    return initialize_account(
        user, password, apps_flyer_user_id, apps_flyer_platform, send_activation_mail, remote_updates
    )


def initialize_account(
    user: User,
    password: str,
    apps_flyer_user_id: str = None,
    apps_flyer_platform: str = None,
    send_activation_mail: bool = True,
    remote_updates: bool = True,
) -> User:

    user.setPassword(password)
    if apps_flyer_user_id and apps_flyer_platform:
        if user.externalIds is None:
            user.externalIds = {}
        user.externalIds["apps_flyer"] = {"user": apps_flyer_user_id, "platform": apps_flyer_platform.upper()}

    repository.save(user)
    logger.info("Created user account", extra={"user": user.id})
    delete_all_users_tokens(user)

    if remote_updates:
        update_external_user(user)

    if not user.isEmailValidated and send_activation_mail:
        request_email_confirmation(user)

    return user


def steps_to_become_beneficiary(user: User) -> list[BeneficiaryValidationStep]:
    missing_steps = []

    if not user.is_phone_validated and FeatureToggle.FORCE_PHONE_VALIDATION.is_active():
        missing_steps.append(BeneficiaryValidationStep.PHONE_VALIDATION)

    beneficiary_import = get_beneficiary_import_for_beneficiary(user)
    if not beneficiary_import:
        missing_steps.append(BeneficiaryValidationStep.ID_CHECK)

    return missing_steps


def validate_phone_number_and_activate_user(user: User, code: str) -> User:
    validate_phone_number(user, code)

    if not steps_to_become_beneficiary(user):
        activate_beneficiary(user)


def update_beneficiary_mandatory_information(
    user: User, address: str, city: str, postal_code: str, activity: str, phone_number: Optional[str] = None
) -> None:
    update_payload = {
        "address": address,
        "city": city,
        "postalCode": postal_code,
        "departementCode": PostalCode(postal_code).get_departement_code(),
        "activity": activity,
        "hasCompletedIdCheck": True,
    }
    if not FeatureToggle.ENABLE_PHONE_VALIDATION.is_active() and not user.phoneNumber and phone_number:
        update_payload["phoneNumber"] = phone_number

    with transaction():
        User.query.filter(User.id == user.id).update(update_payload)
    db.session.refresh(user)

    if not steps_to_become_beneficiary(user):
        check_and_activate_beneficiary(user.id)
    else:
        update_external_user(user)

    logger.info(
        "User id check profile updated",
        extra={"user": user.id, "has_been_activated": user.isBeneficiary},
    )


def update_user_information_from_external_source(
    user: User, data: Union[fraud_models.DMSContent, fraud_models.JouveContent]
) -> User:
    if isinstance(data, fraud_models.DMSContent):
        user = create_beneficiary_from_application(data, user)

    elif isinstance(data, fraud_models.JouveContent):
        if data.activity:
            user.activity = data.activity
        if data.address:
            user.address = data.address
        if data.city:
            user.city = data.city
        if data.gender:
            user.civility = "Mme" if data.gender == "F" else "M."
        if data.birthDateTxt:
            user.dateOfBirth = data.birthDateTxt
        if data.firstName:
            user.firstName = data.firstName
        if data.lastName:
            user.lastName = data.lastName
        if data.postalCode and not user.postalCode:
            user.postalCode = data.postalCode
            user.departementCode = PostalCode(data.postalCode).get_departement_code()
        if data.firstName and data.lastName:
            user.publicName = f"{user.firstName} {user.lastName}"

        if data.bodyPieceNumber:
            items = (
                fraud_api._validate_id_piece_number_format_fraud_item(data.bodyPieceNumber),
                fraud_api._duplicate_id_piece_number_fraud_item(data.bodyPieceNumber),
            )
            if all((item.status == fraud_models.FraudStatus.OK) for item in items):
                user.idPieceNumber = data.bodyPieceNumber

        if not FeatureToggle.ENABLE_PHONE_VALIDATION.is_active():
            if not user.phoneNumber and data.phoneNumber:
                user.phoneNumber = data.phoneNumber

    # update user fields to be correctly initialized
    user.hasSeenTutorials = False
    user.remove_admin_role()

    db.session.add(user)
    db.session.flush()
    return user


def activate_beneficiary(user: User, deposit_source: str = None) -> User:
    if not deposit_source:
        beneficiary_import = get_beneficiary_import_for_beneficiary(user)
        if not beneficiary_import:
            raise exceptions.BeneficiaryImportMissingException()

        deposit_source = beneficiary_import.get_detailed_source()

    user.add_beneficiary_role()

    if "apps_flyer" in user.externalIds:
        log_user_becomes_beneficiary_event_job.delay(user.id)
    deposit = payment_api.create_deposit(user, deposit_source=deposit_source)

    db.session.add_all((user, deposit))
    db.session.commit()
    update_external_user(user)

    logger.info("Activated beneficiary and created deposit", extra={"user": user.id})
    return user


def check_and_activate_beneficiary(userId: int, deposit_source: str = None) -> User:
    with transaction():
        user = get_and_lock_user(userId)
        if user.isBeneficiary or not user.hasCompletedIdCheck:
            db.session.rollback()
            return user
        user = activate_beneficiary(user, deposit_source)
        return user


def attach_beneficiary_import_details(
    beneficiary: User,
    beneficiary_pre_subscription: BeneficiaryPreSubscription,
    status: ImportStatus = ImportStatus.CREATED,
) -> None:
    beneficiary_import = BeneficiaryImport()

    beneficiary_import.applicationId = beneficiary_pre_subscription.application_id
    beneficiary_import.sourceId = beneficiary_pre_subscription.source_id
    beneficiary_import.source = beneficiary_pre_subscription.source

    beneficiary_import.setStatus(status=status)
    beneficiary_import.beneficiary = beneficiary

    repository.save(beneficiary_import)


def request_email_confirmation(user: User) -> None:
    token = create_email_validation_token(user)
    user_emails.send_activation_email(user, native_version=True, token=token)


def request_password_reset(user: User) -> None:
    if not user or not user.isActive:
        return

    is_email_sent = user_emails.send_reset_password_email_to_native_app_user(user)

    if not is_email_sent:
        logger.error("Email service failure when user requested password reset for email '%s'", user.email)
        raise exceptions.EmailNotSent()


def fulfill_account_password(user: User) -> User:
    _generate_random_password(user)
    return user


def fulfill_beneficiary_data(user: User, deposit_source: str, deposit_version: int = None) -> User:
    _generate_random_password(user)

    deposit = payment_api.create_deposit(user, deposit_source, version=deposit_version)
    user.deposits = [deposit]

    return user


def _generate_random_password(user):
    user.password = random_hashed_password()


def suspend_account(user: User, reason: constants.SuspensionReason, actor: User) -> dict[str, int]:
    import pcapi.core.bookings.api as bookings_api  # avoid import loop

    user.isActive = False
    user.suspensionReason = str(reason)
    user.remove_admin_role()
    user.setPassword(secrets.token_urlsafe(30))
    repository.save(user)

    sessions = UserSession.query.filter_by(userId=user.id)
    repository.delete(*sessions)

    n_bookings = 0

    # Cancel all bookings of the related offerer if the suspended
    # account was the last active offerer's account.
    if reason == constants.SuspensionReason.FRAUD:
        for offerer in user.offerers:
            if any(u.isActive and u != user for u in offerer.users):
                continue
            bookings = bookings_repository.find_cancellable_bookings_by_offerer(offerer.id)
            for booking in bookings:
                bookings_api.cancel_booking_for_fraud(booking)
                n_bookings += 1

    # Cancel all bookings of the user (the following works even if the
    # user is not a beneficiary).
    cancel_booking_callback = {
        constants.SuspensionReason.FRAUD: bookings_api.cancel_booking_for_fraud,
        constants.SuspensionReason.UPON_USER_REQUEST: bookings_api.cancel_booking_on_user_requested_account_suspension,
    }.get(reason)
    if cancel_booking_callback:
        for booking in bookings_repository.find_cancellable_bookings_by_beneficiaries([user]):
            cancel_booking_callback(booking)
            n_bookings += 1

    logger.info(
        "Account has been suspended",
        extra={
            "actor": actor.id,
            "user": user.id,
            "reason": str(reason),
        },
    )
    return {"cancelled_bookings": n_bookings}


def unsuspend_account(user: User, actor: User) -> None:
    user.isActive = True
    user.suspensionReason = ""
    repository.save(user)

    logger.info(
        "Account has been unsuspended",
        extra={
            "actor": actor.id,
            "user": user.id,
        },
    )


def send_user_emails_for_email_change(user: User, new_email: str) -> None:
    user_with_new_email = find_user_by_email(new_email)
    if user_with_new_email:
        return

    information_data = build_beneficiary_information_email_change_data(user.firstName)
    information_sucessfully_sent = mails.send(recipients=[user.email], data=information_data)
    if not information_sucessfully_sent:
        raise MailServiceException()

    link_for_email_change = _build_link_for_email_change(user.email, new_email)
    confirmation_data = build_beneficiary_confirmation_email_change_data(
        user.firstName,
        link_for_email_change,
    )
    confirmation_sucessfully_sent = mails.send(recipients=[new_email], data=confirmation_data)
    if not confirmation_sucessfully_sent:
        raise MailServiceException()

    return


def change_user_email(token: str) -> None:
    try:
        jwt_payload = decode_jwt_token(token)
    except (
        ExpiredSignatureError,
        InvalidSignatureError,
        DecodeError,
        InvalidTokenError,
    ) as error:
        raise InvalidTokenError() from error

    if not {"exp", "new_email", "current_email"} <= set(jwt_payload):
        raise InvalidTokenError()

    new_email = sanitize_email(jwt_payload["new_email"])
    if find_user_by_email(new_email):
        return

    current_user = find_user_by_email(jwt_payload["current_email"])
    if not current_user:
        return

    current_user.email = new_email
    sessions = UserSession.query.filter_by(userId=current_user.id)
    repository.delete(*sessions)
    repository.save(current_user)

    logger.info("User has changed their email", extra={"user": current_user.id})

    return


def update_user_info(
    user,
    cultural_survey_filled_date=UNCHANGED,
    cultural_survey_id=UNCHANGED,
    email=UNCHANGED,
    first_name=UNCHANGED,
    has_seen_tutorials=UNCHANGED,
    last_name=UNCHANGED,
    needs_to_fill_cultural_survey=UNCHANGED,
    phone_number=UNCHANGED,
    public_name=UNCHANGED,
):
    if cultural_survey_filled_date is not UNCHANGED:
        user.culturalSurveyFilledDate = cultural_survey_filled_date
    if cultural_survey_id is not UNCHANGED:
        user.culturalSurveyId = cultural_survey_id
    if email is not UNCHANGED:
        user.email = sanitize_email(email)
    if first_name is not UNCHANGED:
        user.firstName = first_name
    if has_seen_tutorials is not UNCHANGED:
        user.hasSeenTutorials = has_seen_tutorials
    if last_name is not UNCHANGED:
        user.lastName = last_name
    if needs_to_fill_cultural_survey is not UNCHANGED:
        user.needsToFillCulturalSurvey = needs_to_fill_cultural_survey
    if phone_number is not UNCHANGED:
        user.phoneNumber = phone_number
    if public_name is not UNCHANGED:
        user.publicName = public_name
    repository.save(user)


def _build_link_for_email_change(current_email: str, new_email: str) -> str:
    expiration_date = datetime.now() + constants.EMAIL_CHANGE_TOKEN_LIFE_TIME
    token = encode_jwt_payload(dict(current_email=current_email, new_email=new_email), expiration_date)

    return f"{get_webapp_url()}/changement-email?token={token}&expiration_timestamp={int(expiration_date.timestamp())}"


def get_domains_credit(user: User, bookings: list[Booking] = None) -> Optional[DomainsCredit]:
    version = user.deposit_version
    if not version or version not in LIMIT_CONFIGURATIONS:
        return None

    if bookings == None:
        bookings = user.get_not_cancelled_bookings()

    config = LIMIT_CONFIGURATIONS[version]

    domains_credit = DomainsCredit(
        all=Credit(
            initial=config.TOTAL_CAP,
            remaining=max(config.TOTAL_CAP - sum(booking.total_amount for booking in bookings), Decimal("0"))
            if user.has_active_deposit
            else Decimal("0"),
        )
    )

    if config.DIGITAL_CAP:
        digital_bookings_total = sum(
            [booking.total_amount for booking in bookings if config.digital_cap_applies(booking.stock.offer)]
        )
        domains_credit.digital = Credit(
            initial=config.DIGITAL_CAP,
            remaining=(
                min(max(config.DIGITAL_CAP - digital_bookings_total, Decimal("0")), domains_credit.all.remaining)
            ),
        )

    if config.PHYSICAL_CAP:
        physical_bookings_total = sum(
            [booking.total_amount for booking in bookings if config.physical_cap_applies(booking.stock.offer)]
        )
        domains_credit.physical = Credit(
            initial=config.PHYSICAL_CAP,
            remaining=(
                min(max(config.PHYSICAL_CAP - physical_bookings_total, Decimal("0")), domains_credit.all.remaining)
            ),
        )

    return domains_credit


def create_pro_user_and_offerer(pro_user: ProUserCreationBodyModel) -> User:
    objects_to_save = []

    new_pro_user = create_pro_user(pro_user)

    existing_offerer = Offerer.query.filter_by(siren=pro_user.siren).one_or_none()

    if existing_offerer:
        user_offerer = _generate_user_offerer_when_existing_offerer(new_pro_user, existing_offerer)
        offerer = existing_offerer
    else:
        offerer = _generate_offerer(pro_user.dict(by_alias=True))
        user_offerer = offerer.grant_access(new_pro_user)
        digital_venue = create_digital_venue(offerer)
        objects_to_save.extend([digital_venue, offerer])
    objects_to_save.append(user_offerer)
    new_pro_user = _set_offerer_departement_code(new_pro_user, offerer)

    objects_to_save.append(new_pro_user)

    repository.save(*objects_to_save)

    try:
        user_emails.send_pro_user_validation_email(new_pro_user)
    except MailServiceException:
        logger.exception("Could not send validation email when creating pro user=%s", new_pro_user.id)

    return new_pro_user


def create_pro_user(pro_user: ProUserCreationBodyModel) -> User:
    new_pro_user = User(from_dict=pro_user.dict(by_alias=True))
    new_pro_user.email = sanitize_email(new_pro_user.email)
    new_pro_user.notificationSubscriptions = asdict(NotificationSubscriptions(marketing_email=pro_user.contact_ok))
    new_pro_user.remove_admin_role()
    new_pro_user.remove_beneficiary_role()
    new_pro_user.needsToFillCulturalSurvey = False
    new_pro_user.generate_validation_token()

    if pro_user.postal_code:
        new_pro_user.departementCode = PostalCode(pro_user.postal_code).get_departement_code()

    if settings.IS_INTEGRATION:
        new_pro_user.add_beneficiary_role()
        deposit = payment_api.create_deposit(new_pro_user, "integration_signup")
        new_pro_user.deposits = [deposit]

    return new_pro_user


def _generate_user_offerer_when_existing_offerer(new_user: User, offerer: Offerer) -> UserOfferer:
    user_offerer = offerer.grant_access(new_user)
    if not settings.IS_INTEGRATION:
        user_offerer.generate_validation_token()
    return user_offerer


def _generate_offerer(data: dict) -> Offerer:
    offerer = Offerer()
    offerer.populate_from_dict(data)

    if not settings.IS_INTEGRATION:
        offerer.generate_validation_token()
    return offerer


def _set_offerer_departement_code(new_user: User, offerer: Offerer) -> User:
    if offerer.postalCode is not None:
        new_user.departementCode = PostalCode(offerer.postalCode).get_departement_code()
    else:
        new_user.departementCode = None
    return new_user


def set_pro_tuto_as_seen(user: User) -> None:
    user.hasSeenProTutorials = True
    repository.save(user)


def change_user_phone_number(user: User, phone_number: str) -> None:
    _check_phone_number_validation_is_authorized(user)

    phone_data = phone_number_utils.ParsedPhoneNumber(phone_number)
    with fraud_manager(user=user, phone_number=phone_data.phone_number):
        check_phone_number_is_legit(phone_data.phone_number, phone_data.country_code)
        check_phone_number_not_used(phone_data.phone_number)

    user.phoneNumber = phone_data.phone_number
    Token.query.filter(Token.user == user, Token.type == TokenType.PHONE_VALIDATION).delete()
    repository.save(user)


def send_phone_validation_code(user: User) -> None:
    _check_phone_number_validation_is_authorized(user)

    phone_data = phone_number_utils.ParsedPhoneNumber(user.phoneNumber)
    with fraud_manager(user=user, phone_number=phone_data.phone_number):
        check_phone_number_is_legit(phone_data.phone_number, phone_data.country_code)
        check_phone_number_not_used(phone_data.phone_number)
        check_sms_sending_is_allowed(user)

    phone_validation_token = create_phone_validation_token(user)
    content = f"{phone_validation_token.value} est ton code de confirmation pass Culture"

    if not send_transactional_sms(phone_data.phone_number, content):
        raise exceptions.PhoneVerificationCodeSendingException()

    update_sent_SMS_counter(app.redis_client, user)


def validate_phone_number(user: User, code: str) -> None:
    _check_phone_number_validation_is_authorized(user)

    phone_data = phone_number_utils.ParsedPhoneNumber(user.phoneNumber)
    with fraud_manager(user=user, phone_number=phone_data.phone_number):
        check_phone_number_is_legit(phone_data.phone_number, phone_data.country_code)
        check_and_update_phone_validation_attempts(app.redis_client, user)

    token = Token.query.filter(
        Token.user == user, Token.value == code, Token.type == TokenType.PHONE_VALIDATION
    ).one_or_none()

    if not token:
        raise exceptions.NotValidCode()

    if token.expirationDate and token.expirationDate < datetime.now():
        raise exceptions.ExpiredCode()

    db.session.delete(token)

    # not wrapped inside a fraud_manager because we don't need to add any fraud
    # log in case this check raises an exception at this point
    check_phone_number_not_used(phone_data.phone_number)

    user.phoneValidationStatus = PhoneValidationStatusType.VALIDATED
    repository.save(user)


def check_phone_number_is_legit(phone_number: str, country_code: str) -> None:
    if phone_number in settings.BLACKLISTED_SMS_RECIPIENTS:
        raise exceptions.BlacklistedPhoneNumber(phone_number)

    if country_code not in constants.WHITELISTED_COUNTRY_PHONE_CODES:
        raise exceptions.InvalidCountryCode(country_code)


def _check_phone_number_validation_is_authorized(user: User) -> None:
    if user.is_phone_validated:
        raise exceptions.UserPhoneNumberAlreadyValidated()

    if not user.isEmailValidated:
        raise exceptions.UnvalidatedEmail()

    if user.isBeneficiary:
        raise exceptions.UserAlreadyBeneficiary()


def check_and_update_phone_validation_attempts(redis: Redis, user: User) -> None:
    phone_validation_attempts_key = f"phone_validation_attempts_user_{user.id}"
    phone_validation_attempts = redis.get(phone_validation_attempts_key)

    if phone_validation_attempts and int(phone_validation_attempts) >= settings.MAX_PHONE_VALIDATION_ATTEMPTS:
        logger.warning(
            "Phone number validation limit reached for user with id=%s",
            user.id,
            extra={"attempts_count": int(phone_validation_attempts)},
        )
        raise exceptions.PhoneValidationAttemptsLimitReached(int(phone_validation_attempts))

    count = redis.incr(phone_validation_attempts_key)
    if count == 1:
        redis.expire(phone_validation_attempts_key, settings.PHONE_VALIDATION_ATTEMPTS_TTL)


def check_phone_number_not_used(phone_number: str) -> None:
    if does_validated_phone_exist(phone_number):
        raise exceptions.PhoneAlreadyExists(phone_number)


def check_sms_sending_is_allowed(user: User) -> None:
    if not is_SMS_sending_allowed(app.redis_client, user):
        raise exceptions.SMSSendingLimitReached()


def get_next_beneficiary_validation_step(user: User) -> Optional[BeneficiaryValidationStep]:
    if user.isBeneficiary or not user.is_eligible:
        return None
    if not user.is_phone_validated and FeatureToggle.ENABLE_PHONE_VALIDATION.is_active():
        return BeneficiaryValidationStep.PHONE_VALIDATION
    if not user.hasCompletedIdCheck:
        return BeneficiaryValidationStep.ID_CHECK

    return None


def validate_token(userId: int, token_value: str) -> Token:
    token = Token.query.filter(
        Token.userId == userId, Token.value == token_value, Token.type == TokenType.ID_CHECK
    ).one_or_none()

    if not token:
        raise exceptions.NotValidCode()

    if token.expirationDate and token.expirationDate < datetime.now() or token.isUsed:
        raise exceptions.ExpiredCode()

    return token


def asynchronous_identity_document_verification(image: bytes, email: str) -> None:
    image_name = f"{random_token(64)}.jpg"
    image_storage_path = f"identity_documents/{image_name}"
    try:
        store_object(
            "identity_documents",
            image_name,
            image,
            content_type="image/jpeg",
            metadata={"email": email},
        )
    except Exception as exception:
        logger.exception("An error has occured while trying to upload image to encrypted gcp bucket: %s", exception)
        raise exceptions.IdentityDocumentUploadException()

    try:
        verify_identity_document.delay(VerifyIdentityDocumentRequest(image_storage_path=image_storage_path))
    except Exception as exception:
        logger.exception("An error has occured while trying to add cloudtask in queue: %s", exception)
        delete_object(image_storage_path)
        raise exceptions.CloudTaskCreationException()
    return


def _get_identity_document_informations(image_storage_path: str) -> Tuple[str, bytes]:
    image_blob: Blob = get_object(image_storage_path)
    if not image_blob:
        # This means the image cannot be downloaded.
        # It either has been treated or there is a network problem
        raise exceptions.IdentityDocumentVerificationException()
    email = image_blob.metadata.get("email", "").strip()
    if email == "":
        raise exceptions.MissingEmailInMetadataException()
    image = image_blob.download_as_bytes()

    return (email, image)


def verify_identity_document_informations(image_storage_path: str) -> None:
    email, image = _get_identity_document_informations(image_storage_path)
    valid, code = ask_for_identity_document_verification(email, image)
    if not valid:
        user_emails.send_document_verification_error_email(email, code)
        fraud_api.handle_document_validation_error(email, code)
    delete_object(image_storage_path)


@contextmanager
def fraud_manager(user: User, phone_number: str) -> typing.Generator:
    try:
        yield
    except exceptions.BlacklistedPhoneNumber:
        fraud_api.handle_blacklisted_sms_recipient(user, phone_number)
        raise
    except exceptions.PhoneAlreadyExists:
        fraud_api.handle_phone_already_exists(user, phone_number)
        raise
    except exceptions.SMSSendingLimitReached:
        fraud_api.handle_sms_sending_limit_reached(user)
        raise
    except exceptions.PhoneValidationAttemptsLimitReached as error:
        fraud_api.handle_phone_validation_attempts_limit_reached(user, error.attempts)
        raise
