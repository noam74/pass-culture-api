from datetime import datetime
from unittest.mock import MagicMock
from unittest.mock import call
from unittest.mock import patch

from freezegun import freeze_time
import pytest

from pcapi.connectors.beneficiaries.jouve_backend import ApiJouveException
from pcapi.connectors.beneficiaries.jouve_backend import BeneficiaryJouveBackend
from pcapi.connectors.beneficiaries.jouve_backend import FraudControlException
from pcapi.domain.beneficiary_pre_subscription.beneficiary_pre_subscription import BeneficiaryPreSubscription


# Required by the feature flag...
pytestmark = pytest.mark.usefixtures("db_session")


def get_application_by_detail_response(application_id: int = 2, birth_date: str = "09/08/1995", **kwargs) -> dict:
    return {
        "id": application_id,
        "birthDate": birth_date,
        "registrationDate": "04/06/2020 06:00",
        "address": "18 avenue des fleurs",
        "city": "RENNES",
        "email": "rennes@example.org",
        "firstName": "Céline",
        "gender": "F",
        "lastName": "DURAND",
        "postalCode": "35123",
        "phoneNumber": "0123456789",
        "activity": "Apprenti",
        "birthLocationCtrl": "OK",
        "posteCodeCtrl": "OK",
        "serviceCodeCtrl": "OK",
        **kwargs,
    }


def get_token_detail_response(token: str) -> dict:
    return {"Value": token}


@freeze_time("2020-10-15 09:00:00")
@patch("pcapi.settings.JOUVE_API_DOMAIN", "https://jouve.com")
@patch("pcapi.settings.JOUVE_API_PASSWORD", "secret-password")
@patch("pcapi.settings.JOUVE_API_USERNAME", "username")
@patch("pcapi.settings.JOUVE_API_VAULT_GUID", "12")
@patch("pcapi.settings.IS_PROD", True)
@patch("pcapi.connectors.beneficiaries.jouve_backend.requests.post")
def test_calls_jouve_api_with_previously_fetched_token(mocked_requests_post):
    # Given
    token = "token-for-tests"
    application_id = 5

    get_token_response = MagicMock(status_code=200)
    get_token_response.json = MagicMock(return_value=get_token_detail_response(token))

    get_application_by_json = get_application_by_detail_response(
        application_id=application_id,
        birth_date="08/24/1995",
    )
    get_application_by_response = MagicMock(status_code=200)
    get_application_by_response.json = MagicMock(return_value=get_application_by_json)

    mocked_requests_post.side_effect = [get_token_response, get_application_by_response]

    # When
    beneficiary_pre_subscription = BeneficiaryJouveBackend().get_application_by(application_id)

    # Then
    assert mocked_requests_post.call_args_list[0] == call(
        "https://jouve.com/REST/server/authenticationtokens",
        headers={"Content-Type": "application/json"},
        json={
            "Username": "username",
            "Password": "secret-password",
            "VaultGuid": "12",
            "Expiration": "2020-10-15T10:00:00",
        },
    )
    assert mocked_requests_post.call_args_list[1] == call(
        "https://jouve.com/REST/vault/extensionmethod/VEM_GetJeuneByID",
        data=str(application_id),
        headers={"X-Authentication": token},
    )
    assert isinstance(beneficiary_pre_subscription, BeneficiaryPreSubscription)
    assert beneficiary_pre_subscription.activity == "Apprenti"
    assert beneficiary_pre_subscription.address == "18 avenue des fleurs"
    assert beneficiary_pre_subscription.application_id == 5
    assert beneficiary_pre_subscription.city == "RENNES"
    assert beneficiary_pre_subscription.civility == "Mme"
    assert beneficiary_pre_subscription.date_of_birth == datetime(1995, 8, 24)
    assert beneficiary_pre_subscription.department_code == "35"
    assert beneficiary_pre_subscription.email == "rennes@example.org"
    assert beneficiary_pre_subscription.first_name == "Céline"
    assert beneficiary_pre_subscription.last_name == "DURAND"
    assert beneficiary_pre_subscription.phone_number == "0123456789"
    assert beneficiary_pre_subscription.postal_code == "35123"
    assert beneficiary_pre_subscription.public_name == "Céline DURAND"


class FraudControlsTest:
    def _generate_requests_mocks(self, application):
        get_token_response = MagicMock(status_code=200)
        get_application_by_response = MagicMock(status_code=200)
        get_application_by_response.json = MagicMock(return_value=application)
        return [get_token_response, get_application_by_response]

    @patch("pcapi.connectors.beneficiaries.jouve_backend.requests.post")
    def test_reject_application_when_birth_location_ko(self, mocked_requests_post):
        mocked_requests_post.side_effect = self._generate_requests_mocks(
            get_application_by_detail_response(birthLocationCtrl="KO")
        )

        beneficiary_pre_subscription = BeneficiaryJouveBackend().get_application_by(5)

        assert isinstance(beneficiary_pre_subscription, BeneficiaryPreSubscription)

    @patch("pcapi.connectors.beneficiaries.jouve_backend.requests.post")
    def test_reject_application_when_post_code_ko(self, mocked_requests_post):
        mocked_requests_post.side_effect = self._generate_requests_mocks(
            get_application_by_detail_response(posteCodeCtrl="KO")
        )
        with pytest.raises(FraudControlException):
            BeneficiaryJouveBackend().get_application_by(5)

    @patch("pcapi.connectors.beneficiaries.jouve_backend.requests.post")
    def test_reject_application_when_service_code_ko(self, mocked_requests_post):
        mocked_requests_post.side_effect = self._generate_requests_mocks(
            get_application_by_detail_response(serviceCodeCtrl="KO")
        )
        with pytest.raises(FraudControlException):
            BeneficiaryJouveBackend().get_application_by(5)


@patch("pcapi.connectors.beneficiaries.jouve_backend.requests.post")
def test_raise_exception_when_password_is_invalid(stubed_requests_post):
    # Given
    application_id = "5"
    stubed_requests_post.return_value = MagicMock(status_code=400)

    # When
    with pytest.raises(ApiJouveException) as api_jouve_exception:
        BeneficiaryJouveBackend().get_application_by(application_id)

    # Then
    assert str(api_jouve_exception.value) == "Error 400 getting API jouve authentication token"


@patch("pcapi.connectors.beneficiaries.jouve_backend.requests.post")
def test_raise_exception_when_token_is_invalid(stubed_requests_post):
    # Given
    token = "token-for-tests"
    application_id = "5"

    get_token_response = MagicMock(status_code=200)
    get_token_response.json = MagicMock(return_value=get_token_detail_response(token))

    get_application_by_json = get_application_by_detail_response()
    get_application_by_response = MagicMock(status_code=400)
    get_application_by_response.json = MagicMock(return_value=get_application_by_json)

    stubed_requests_post.side_effect = [get_token_response, get_application_by_response]

    # When
    with pytest.raises(ApiJouveException) as api_jouve_exception:
        BeneficiaryJouveBackend().get_application_by(application_id)

    # Then
    assert str(api_jouve_exception.value) == "Error 400 getting API jouve GetJouveByID with id: 5"
