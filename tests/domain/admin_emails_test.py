from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import patch

from pcapi.domain.admin_emails import maybe_send_offerer_validation_email
from pcapi.domain.admin_emails import send_offer_creation_notification_to_administration
from pcapi.domain.admin_emails import send_payment_details_email
from pcapi.domain.admin_emails import send_payment_message_email
from pcapi.domain.admin_emails import send_payments_report_emails
from pcapi.domain.admin_emails import send_wallet_balances_email
from pcapi.model_creators.generic_creators import create_offerer
from pcapi.model_creators.generic_creators import create_user
from pcapi.model_creators.generic_creators import create_user_offerer
from pcapi.model_creators.generic_creators import create_venue
from pcapi.model_creators.specific_creators import create_offer_with_thing_product
from pcapi.utils.mailing import MailServiceException


@patch("pcapi.connectors.api_entreprises.requests.get")
def test_maybe_send_offerer_validation_email_sends_email_to_pass_culture_when_objects_to_validate_and_send_email_enabled(
    mock_api_entreprise, app
):
    # Given
    response_return_value = MagicMock(status_code=200, text="")
    response_return_value.json = MagicMock(
        return_value={"unite_legale": {"etablissement_siege": {}, "etablissements": []}}
    )
    mock_api_entreprise.return_value = response_return_value

    offerer = create_offerer(validation_token="12345")
    user = create_user(validation_token="98765")
    user_offerer = create_user_offerer(user, offerer)

    mocked_send_email = Mock()
    return_value = Mock()
    return_value.status_code = 200
    mocked_send_email.return_value = return_value

    # When
    with patch("pcapi.utils.mailing.feature_send_mail_to_users_enabled", return_value=True):
        maybe_send_offerer_validation_email(offerer, user_offerer, mocked_send_email)

    # Then
    mocked_send_email.assert_called_once()
    args = mocked_send_email.call_args
    email = args[1]["data"]
    assert email["To"] == "administration@example.com"
    assert "This is a test" not in email["Html-part"]


@patch("pcapi.connectors.api_entreprises.requests.get")
def test_maybe_send_offerer_validation_email_sends_email_to_pass_culture_dev_when_objects_to_validate_and_send_email_disabled(
    mock_api_entreprise, app
):
    # Given
    response_return_value = MagicMock(status_code=200, text="")
    response_return_value.json = MagicMock(
        return_value={"unite_legale": {"etablissement_siege": {}, "etablissements": []}}
    )
    mock_api_entreprise.return_value = response_return_value

    offerer = create_offerer(validation_token="12345")

    user = create_user(validation_token="98765")

    user_offerer = create_user_offerer(user, offerer)

    mocked_send_email = Mock()
    return_value = Mock()
    return_value.status_code = 200
    mocked_send_email.return_value = return_value

    # When
    with patch("pcapi.utils.mailing.feature_send_mail_to_users_enabled", return_value=False):
        maybe_send_offerer_validation_email(offerer, user_offerer, mocked_send_email)

    # Then
    mocked_send_email.assert_called_once()
    args = mocked_send_email.call_args
    email = args[1]["data"]
    assert email["To"] == "dev@example.com"
    assert "This is a test" in email["Html-part"]


def test_maybe_send_offerer_validation_email_does_not_send_email_if_all_validated(app):
    # Given
    offerer = create_offerer(
        siren="732075312",
        address="122 AVENUE DE FRANCE",
        city="Paris",
        postal_code="75013",
        name="Accenture",
        validation_token=None,
    )

    user = create_user(
        can_book_free_offers=False,
        departement_code="75",
        email="user@accenture.com",
        public_name="Test",
        validation_token=None,
    )

    user_offerer = create_user_offerer(user, offerer, validation_token=None)

    mocked_send_email = Mock()
    return_value = Mock()
    return_value.status_code = 200
    mocked_send_email.return_value = return_value

    # When
    try:
        maybe_send_offerer_validation_email(offerer, user_offerer, mocked_send_email)
    except MailServiceException as e:
        app.logger.error("Mail service failure", e)

    # Then
    assert not mocked_send_email.called


def test_send_payment_details_email_when_mailjet_status_code_200_sends_email_to_pass_culture(app):
    # Given
    csv = '"header A","header B","header C","header D"\n"part A","part B","part C","part D"\n'
    recipients = ["comptable1@culture.fr", "comptable2@culture.fr"]

    mocked_send_email = Mock()
    return_value = Mock()
    return_value.status_code = 200
    mocked_send_email.return_value = return_value

    # When
    with patch("pcapi.utils.mailing.feature_send_mail_to_users_enabled", return_value=True):
        send_payment_details_email(csv, recipients, mocked_send_email)

    # Then
    mocked_send_email.assert_called_once()
    args = mocked_send_email.call_args
    email = args[1]["data"]
    assert email["To"] == "comptable1@culture.fr, comptable2@culture.fr"


def test_send_payment_details_email_has_pass_culture_dev_as_recipient_when_send_email_disabled(app):
    # Given
    csv = '"header A","header B","header C","header D"\n"part A","part B","part C","part D"\n'
    recipients = ["comptable1@culture.fr", "comptable2@culture.fr"]

    mocked_send_email = Mock()
    return_value = Mock()
    return_value.status_code = 200
    mocked_send_email.return_value = return_value

    # When
    with patch("pcapi.utils.mailing.feature_send_mail_to_users_enabled", return_value=False):
        send_payment_details_email(csv, recipients, mocked_send_email)

    # Then
    mocked_send_email.assert_called_once()
    args = mocked_send_email.call_args
    email = args[1]["data"]
    assert email["To"] == "dev@example.com"


def test_send_wallet_balances_email_when_mailjet_status_code_200_sends_email_to_recipients(app):
    # Given
    csv = '"header A","header B","header C","header D"\n"part A","part B","part C","part D"\n'
    recipients = ["comptable1@culture.fr", "comptable2@culture.fr"]

    mocked_send_email = Mock()
    return_value = Mock()
    return_value.status_code = 200
    mocked_send_email.return_value = return_value

    # When
    with patch("pcapi.utils.mailing.feature_send_mail_to_users_enabled", return_value=True):
        send_wallet_balances_email(csv, recipients, mocked_send_email)

    # Then
    mocked_send_email.assert_called_once()
    args = mocked_send_email.call_args
    email = args[1]["data"]
    assert email["To"] == "comptable1@culture.fr, comptable2@culture.fr"


def test_send_wallet_balances_email_has_pass_culture_dev_as_recipient_when_send_email_disabled(app):
    # Given
    csv = '"header A","header B","header C","header D"\n"part A","part B","part C","part D"\n'
    recipients = ["comptable1@culture.fr", "comptable2@culture.fr"]

    mocked_send_email = Mock()
    return_value = Mock()
    return_value.status_code = 200
    mocked_send_email.return_value = return_value

    # When
    with patch("pcapi.utils.mailing.feature_send_mail_to_users_enabled", return_value=False):
        send_wallet_balances_email(csv, recipients, mocked_send_email)

    # Then
    mocked_send_email.assert_called_once()
    args = mocked_send_email.call_args
    email = args[1]["data"]
    assert email["To"] == "dev@example.com"


def test_send_payments_report_emails_when_mailjet_status_code_200_sends_email_to_recipients(app):
    # Given
    not_processable_csv = '"header A","header B","header C","header D"\n"part A","part B","part C","part D"\n'
    error_csv = '"header 1","header 2","header 3","header 4"\n"part 1","part 2","part 3","part 4"\n'
    grouped_payments = {"ERROR": [Mock(), Mock()], "SENT": [Mock()], "PENDING": [Mock(), Mock(), Mock()]}

    mocked_send_email = Mock()
    return_value = Mock()
    return_value.status_code = 200
    mocked_send_email.return_value = return_value

    # When
    with patch("pcapi.utils.mailing.feature_send_mail_to_users_enabled", return_value=True):
        send_payments_report_emails(
            not_processable_csv, error_csv, grouped_payments, ["dev.team@test.com"], mocked_send_email
        )

    # Then
    mocked_send_email.assert_called_once()
    args = mocked_send_email.call_args
    email = args[1]["data"]
    assert email["To"] == "dev.team@test.com"


def test_send_payments_report_emails_email_has_pass_culture_dev_as_recipient_when_send_email_disabled(app):
    # Given
    not_processable_csv = '"header A","header B","header C","header D"\n"part A","part B","part C","part D"\n'
    error_csv = '"header 1","header 2","header 3","header 4"\n"part 1","part 2","part 3","part 4"\n'
    grouped_payments = {"ERROR": [Mock(), Mock()], "SENT": [Mock()], "PENDING": [Mock(), Mock(), Mock()]}

    mocked_send_email = Mock()
    return_value = Mock()
    return_value.status_code = 200
    mocked_send_email.return_value = return_value

    # When
    with patch("pcapi.utils.mailing.feature_send_mail_to_users_enabled", return_value=False):
        send_payments_report_emails(
            not_processable_csv, error_csv, grouped_payments, ["dev.team@test.com"], mocked_send_email
        )

    # Then
    mocked_send_email.assert_called_once()
    args = mocked_send_email.call_args
    email = args[1]["data"]
    assert email["To"] == "dev@example.com"


class SendOfferCreationNotificationToAdministrationTest:
    def test_when_mailjet_status_code_200_sends_email_to_administration_email(self, app):
        mocked_send_email = Mock()
        return_value = Mock()
        return_value.status_code = 200
        mocked_send_email.return_value = return_value
        offerer = create_offerer()
        venue = create_venue(offerer)
        offer = create_offer_with_thing_product(venue)
        author = create_user(email="author@email.com")
        # When
        with patch("pcapi.utils.mailing.feature_send_mail_to_users_enabled", return_value=True):
            send_offer_creation_notification_to_administration(offer, author, mocked_send_email)

        # Then
        mocked_send_email.assert_called_once()
        args = mocked_send_email.call_args
        email = args[1]["data"]
        assert email["To"] == "administration@example.com"

    def test_when_send_email_disabled_has_pass_culture_dev_as_recipient(self, app):
        # Given
        mocked_send_email = Mock()
        return_value = Mock()
        return_value.status_code = 200
        mocked_send_email.return_value = return_value
        offerer = create_offerer()
        venue = create_venue(offerer)
        offer = create_offer_with_thing_product(venue)
        author = create_user(email="author@email.com")
        # When
        with patch("pcapi.utils.mailing.feature_send_mail_to_users_enabled", return_value=False):
            send_offer_creation_notification_to_administration(offer, author, mocked_send_email)

        # Then
        mocked_send_email.assert_called_once()
        args = mocked_send_email.call_args
        email = args[1]["data"]
        assert email["To"] == "dev@example.com"


class SendPaymentMessageEmailTest:
    @patch(
        "pcapi.domain.admin_emails.make_payment_message_email",
        return_value={"Html-part": "<html><body></body></html>", "To": "em@ail.com"},
    )
    def test_returns_true_if_email_was_sent(self, make_payment_transaction_email):
        # given
        xml = '<?xml version="1.0" encoding="UTF-8"?><Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.001.001.03"></Document>'
        checksum = b"\x16\x91\x0c\x11~Hs\xc5\x1a\xa3W1\x13\xbf!jq@\xea  <h&\xef\x1f\xaf\xfc\x7fO\xc8\x82"
        recipients = ["test@email"]
        mocked_send_email = Mock()
        mocked_send_email.return_value = True
        # when
        successfully_sent = send_payment_message_email(xml, checksum, recipients, mocked_send_email)

        # then
        assert successfully_sent

    @patch(
        "pcapi.domain.admin_emails.make_payment_message_email",
        return_value={"Html-part": "<html><body></body></html>", "To": "em@ail.com"},
    )
    def test_returns_false_if_not_email_was_sent(self, make_payment_transaction_email):
        # given
        xml = '<?xml version="1.0" encoding="UTF-8"?><Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.001.001.03"></Document>'
        checksum = b"\x16\x91\x0c\x11~Hs\xc5\x1a\xa3W1\x13\xbf!jq@\xea  <h&\xef\x1f\xaf\xfc\x7fO\xc8\x82"
        recipients = ["test@email"]
        mocked_send_email = Mock()
        mocked_send_email.return_value = False
        # when
        successfully_sent = send_payment_message_email(xml, checksum, recipients, mocked_send_email)

        # then
        assert not successfully_sent
