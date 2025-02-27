import logging
import typing

from pcapi.core import mails
from pcapi.core.bookings.models import Booking
from pcapi.core.bookings.models import BookingCancellationReasons
from pcapi.core.offerers.models import Offerer
from pcapi.core.offers.models import OfferValidationStatus
from pcapi.core.users import api as users_api
from pcapi.core.users import models as users_models
from pcapi.core.users.models import Token
from pcapi.core.users.models import User
from pcapi.domain.beneficiary_pre_subscription.model import BeneficiaryPreSubscription
from pcapi.emails import beneficiary_activation
from pcapi.emails.beneficiary_booking_cancellation import make_beneficiary_booking_cancellation_email_data
from pcapi.emails.beneficiary_booking_confirmation import retrieve_data_for_beneficiary_booking_confirmation_email
from pcapi.emails.beneficiary_expired_bookings import build_expired_bookings_recap_email_data_for_beneficiary
from pcapi.emails.beneficiary_offer_cancellation import (
    retrieve_offerer_booking_recap_email_data_after_user_cancellation,
)
from pcapi.emails.beneficiary_pre_subscription_rejected import (
    make_not_eligible_beneficiary_pre_subscription_rejected_data,
)
from pcapi.emails.beneficiary_pre_subscription_rejected import make_dms_wrong_values_data
from pcapi.emails.beneficiary_pre_subscription_rejected import make_duplicate_beneficiary_pre_subscription_rejected_data
from pcapi.emails.beneficiary_pre_subscription_rejected import make_fraud_suspicion_data
from pcapi.emails.beneficiary_soon_to_be_expired_bookings import (
    build_soon_to_be_expired_bookings_recap_email_data_for_beneficiary,
)
from pcapi.emails.beneficiary_warning_after_pro_booking_cancellation import (
    retrieve_data_to_warn_beneficiary_after_pro_booking_cancellation,
)
from pcapi.emails.new_offer_validation import retrieve_data_for_offer_approval_email
from pcapi.emails.new_offer_validation import retrieve_data_for_offer_rejection_email
from pcapi.emails.new_offerer_validated_withdrawal_terms import (
    retrieve_data_for_new_offerer_validated_withdrawal_terms_email,
)
from pcapi.emails.offer_webapp_link import build_data_for_offer_webapp_link
from pcapi.emails.offerer_booking_recap import retrieve_data_for_offerer_booking_recap_email
from pcapi.emails.offerer_bookings_recap_after_deleting_stock import (
    retrieve_offerer_bookings_recap_email_data_after_offerer_cancellation,
)
from pcapi.emails.offerer_expired_bookings import build_expired_bookings_recap_email_data_for_offerer
from pcapi.emails.pro_reset_password import retrieve_data_for_reset_password_link_to_admin_email
from pcapi.emails.pro_reset_password import retrieve_data_for_reset_password_pro_email
from pcapi.emails.user_document_validation import build_data_for_document_verification_error
from pcapi.emails.user_notification_after_stock_update import (
    retrieve_data_to_warn_user_after_stock_update_affecting_booking,
)
from pcapi.emails.user_reset_password import retrieve_data_for_reset_password_native_app_email
from pcapi.emails.user_reset_password import retrieve_data_for_reset_password_user_email
from pcapi.models import Offer
from pcapi.repository.offerer_queries import find_new_offerer_user_email
from pcapi.utils.mailing import make_admin_user_validation_email
from pcapi.utils.mailing import make_offerer_driven_cancellation_email_for_offerer
from pcapi.utils.mailing import make_pro_user_validation_email


logger = logging.getLogger(__name__)


def send_booking_confirmation_email_to_offerer(booking: Booking) -> None:
    offerer_booking_email = booking.stock.offer.bookingEmail
    if offerer_booking_email:
        data = retrieve_data_for_offerer_booking_recap_email(booking)
        mails.send(recipients=[offerer_booking_email], data=data)


def send_booking_confirmation_email_to_beneficiary(booking: Booking) -> None:
    data = retrieve_data_for_beneficiary_booking_confirmation_email(booking)
    mails.send(recipients=[booking.user.email], data=data)


def send_beneficiary_booking_cancellation_email(booking: Booking) -> None:
    data = make_beneficiary_booking_cancellation_email_data(booking)
    mails.send(recipients=[booking.user.email], data=data)


def send_user_webapp_offer_link_email(user: User, offer: Offer) -> None:
    data = build_data_for_offer_webapp_link(user, offer)
    mails.send(recipients=[user.email], data=data)


def send_user_driven_cancellation_email_to_offerer(booking: Booking) -> None:
    offerer_booking_email = booking.stock.offer.bookingEmail
    if offerer_booking_email:
        data = retrieve_offerer_booking_recap_email_data_after_user_cancellation(booking)
        mails.send(recipients=[offerer_booking_email], data=data)


def send_offerer_driven_cancellation_email_to_offerer(booking: Booking) -> None:
    offerer_booking_email = booking.stock.offer.bookingEmail
    if offerer_booking_email:
        email = make_offerer_driven_cancellation_email_for_offerer(booking)
        mails.send(recipients=[offerer_booking_email], data=email)


def send_warning_to_beneficiary_after_pro_booking_cancellation(booking: Booking) -> None:
    data = retrieve_data_to_warn_beneficiary_after_pro_booking_cancellation(booking)
    mails.send(recipients=[booking.user.email], data=data)


def send_reset_password_email_to_user(user: User) -> bool:
    token = users_api.create_reset_password_token(user)
    data = retrieve_data_for_reset_password_user_email(user, token)
    return mails.send(recipients=[user.email], data=data)


def send_reset_password_email_to_native_app_user(user: User) -> bool:
    token = users_api.create_reset_password_token(user)
    data = retrieve_data_for_reset_password_native_app_email(user, token)
    return mails.send(recipients=[user.email], data=data)


def send_reset_password_email_to_pro(user: User) -> None:
    token = users_api.create_reset_password_token(user)
    data = retrieve_data_for_reset_password_pro_email(user, token)
    mails.send(recipients=[user.email], data=data)


def send_offerer_bookings_recap_email_after_offerer_cancellation(bookings: list[Booking]) -> None:
    offerer_booking_email = bookings[0].stock.offer.bookingEmail
    if offerer_booking_email:
        data = retrieve_offerer_bookings_recap_email_data_after_offerer_cancellation(bookings)
        mails.send(recipients=[offerer_booking_email], data=data)


def send_booking_cancellation_emails_to_user_and_offerer(
    booking: Booking,
    reason: BookingCancellationReasons,
) -> None:
    if reason == BookingCancellationReasons.BENEFICIARY:
        send_beneficiary_booking_cancellation_email(booking)
        send_user_driven_cancellation_email_to_offerer(booking)
    if reason == BookingCancellationReasons.OFFERER:
        send_warning_to_beneficiary_after_pro_booking_cancellation(booking)
        send_offerer_driven_cancellation_email_to_offerer(booking)
    if reason == BookingCancellationReasons.FRAUD:
        send_user_driven_cancellation_email_to_offerer(booking)


def send_expired_bookings_recap_email_to_beneficiary(beneficiary: User, bookings: list[Booking]) -> None:
    data = build_expired_bookings_recap_email_data_for_beneficiary(beneficiary, bookings)
    mails.send(recipients=[beneficiary.email], data=data)


def send_expired_bookings_recap_email_to_offerer(offerer: Offerer, bookings: list[Booking]) -> None:
    offerer_booking_email = bookings[0].stock.offer.bookingEmail
    if offerer_booking_email:
        data = build_expired_bookings_recap_email_data_for_offerer(offerer, bookings)
        mails.send(recipients=[offerer_booking_email], data=data)


def send_pro_user_validation_email(user: User) -> None:
    data = make_pro_user_validation_email(user)
    mails.send(recipients=[user.email], data=data)


def send_admin_user_validation_email(user: User, token: Token) -> None:
    data = make_admin_user_validation_email(user, token.value)
    mails.send(recipients=[user.email], data=data)


def send_soon_to_be_expired_bookings_recap_email_to_beneficiary(beneficiary: User, bookings: list[Booking]) -> None:
    data = build_soon_to_be_expired_bookings_recap_email_data_for_beneficiary(beneficiary, bookings)
    mails.send(recipients=[beneficiary.email], data=data)


def send_activation_email(
    user: User,
    token: users_models.Token,
    native_version: bool = False,
) -> bool:
    if not native_version:
        data = beneficiary_activation.get_activation_email_data(user=user, token=token)
    else:
        data = beneficiary_activation.get_activation_email_data_for_native(user=user, token=token)
    return mails.send(recipients=[user.email], data=data)


def send_accepted_as_beneficiary_email(user: User) -> bool:
    data = beneficiary_activation.get_accepted_as_beneficiary_email_data()
    return mails.send(recipients=[user.email], data=data)


def send_batch_stock_postponement_emails_to_users(bookings: list[Booking]) -> None:
    for booking in bookings:
        send_booking_postponement_emails_to_users(booking)


def send_booking_postponement_emails_to_users(booking: Booking) -> None:
    data = retrieve_data_to_warn_user_after_stock_update_affecting_booking(booking)
    mails.send(recipients=[booking.user.email], data=data)


def send_rejection_email_to_beneficiary_pre_subscription(
    beneficiary_pre_subscription: BeneficiaryPreSubscription,
    beneficiary_is_eligible: bool,
) -> None:
    if not beneficiary_is_eligible:
        data = make_not_eligible_beneficiary_pre_subscription_rejected_data()
    else:
        data = make_duplicate_beneficiary_pre_subscription_rejected_data()
    mails.send(recipients=[beneficiary_pre_subscription.email], data=data)


def send_fraud_suspicion_email(
    beneficiary_pre_subscription: BeneficiaryPreSubscription,
) -> None:
    data = make_fraud_suspicion_data()
    mails.send(recipients=[beneficiary_pre_subscription.email], data=data)


def send_newly_eligible_user_email(user: User) -> bool:
    data = beneficiary_activation.get_newly_eligible_user_email_data(user)
    return mails.send(recipients=[user.email], data=data)


def send_reset_password_link_to_admin_email(created_user: User, admin_email: User, reset_password_link: str) -> bool:
    data = retrieve_data_for_reset_password_link_to_admin_email(created_user, reset_password_link)
    return mails.send(recipients=[admin_email], data=data)


def send_offer_validation_status_update_email(
    offer: Offer, validation_status: OfferValidationStatus, recipient_emails: list[str]
) -> bool:
    if validation_status is OfferValidationStatus.APPROVED:
        offer_data = retrieve_data_for_offer_approval_email(offer)
        return mails.send(recipients=recipient_emails, data=offer_data)

    if validation_status is OfferValidationStatus.REJECTED:
        offer_data = retrieve_data_for_offer_rejection_email(offer)
        return mails.send(recipients=recipient_emails, data=offer_data)
    return False


def send_document_verification_error_email(email: str, code: str) -> bool:
    data = build_data_for_document_verification_error(code)
    return mails.send(recipients=[email], data=data)


def send_withdrawal_terms_to_newly_validated_offerer(offerer: Offerer) -> None:
    offerer_email = find_new_offerer_user_email(offerer.id)
    data = retrieve_data_for_new_offerer_validated_withdrawal_terms_email()
    mails.send(recipients=[offerer_email], data=data)


def send_dms_application_emails(users: typing.Iterable[User]) -> None:
    data = beneficiary_activation.get_dms_application_data()
    mails.send(recipients=[user.email for user in users], data=data)


def send_dms_wrong_values_emails(
    user_email: str, postal_code: typing.Optional[str], id_piece_number: typing.Optional[str]
) -> None:
    data = make_dms_wrong_values_data(postal_code, id_piece_number)
    mails.send(recipients=[user_email], data=data)
