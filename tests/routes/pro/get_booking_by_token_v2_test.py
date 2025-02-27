from datetime import datetime
from datetime import timedelta
from unittest import mock

from freezegun import freeze_time
import pytest

import pcapi.core.bookings.factories as bookings_factories
from pcapi.core.categories import subcategories
import pcapi.core.educational.factories as educational_factories
from pcapi.core.educational.models import EducationalBookingStatus
from pcapi.core.offerers.factories import ApiKeyFactory
import pcapi.core.offers.factories as offers_factories
import pcapi.core.users.factories as users_factories
from pcapi.model_creators.generic_creators import create_booking
from pcapi.model_creators.generic_creators import create_offerer
from pcapi.model_creators.generic_creators import create_payment
from pcapi.model_creators.generic_creators import create_user_offerer
from pcapi.model_creators.generic_creators import create_venue
from pcapi.model_creators.specific_creators import create_event_occurrence
from pcapi.model_creators.specific_creators import create_offer_with_event_product
from pcapi.model_creators.specific_creators import create_stock_from_event_occurrence
from pcapi.model_creators.specific_creators import create_stock_with_event_offer
from pcapi.model_creators.specific_creators import create_stock_with_thing_offer
from pcapi.models import api_errors
from pcapi.repository import repository
from pcapi.utils.date import format_into_utc_date
from pcapi.utils.human_ids import humanize

from tests.conftest import TestClient


pytestmark = pytest.mark.usefixtures("db_session")


class Returns200Test:
    @freeze_time("2019-11-26 18:29:20.891028")
    def test_when_user_has_rights_and_regular_offer(self, app):
        # Given
        user = users_factories.BeneficiaryFactory(email="user@example.com", publicName="John Doe")
        admin_user = users_factories.AdminFactory(email="admin@example.com")
        offerer = create_offerer()
        create_user_offerer(admin_user, offerer)
        venue = create_venue(offerer, name="Venue name", address="Venue address")
        offer = create_offer_with_event_product(
            venue=venue,
            event_name="Event Name",
            event_subcategory_id=subcategories.SEANCE_CINE.id,
            extra_data={
                "theater": {
                    "allocine_movie_id": 165,
                    "allocine_room_id": 987,
                }
            },
        )
        four_days_from_now = datetime.utcnow() + timedelta(days=4)
        event_occurrence = create_event_occurrence(offer, beginning_datetime=four_days_from_now)
        stock = create_stock_from_event_occurrence(event_occurrence, price=12)
        unconfirmed_booking = create_booking(
            user=user, quantity=3, stock=stock, venue=venue, date_created=datetime.utcnow() - timedelta(hours=48)
        )
        repository.save(unconfirmed_booking)
        url = f"/v2/bookings/token/{unconfirmed_booking.token}"

        # When
        response = TestClient(app.test_client()).with_basic_auth("admin@example.com").get(url)

        # Then
        assert response.headers["Content-type"] == "application/json"
        assert response.status_code == 200
        assert response.json == {
            "bookingId": humanize(unconfirmed_booking.id),
            "dateOfBirth": "",
            "datetime": format_into_utc_date(stock.beginningDatetime),
            "ean13": "",
            "email": "user@example.com",
            "formula": "PLACE",
            "isUsed": False,
            "offerId": offer.id,
            "offerName": "Event Name",
            "offerType": "EVENEMENT",
            "phoneNumber": "",
            "price": 12.0,
            "publicOfferId": humanize(offer.id),
            "quantity": 3,
            "theater": {
                "allocine_movie_id": 165,
                "allocine_room_id": 987,
            },
            "userName": "John Doe",
            "venueAddress": "Venue address",
            "venueDepartementCode": "93",
            "venueName": "Venue name",
        }

    def test_when_user_has_rights_and_booking_is_educational_validated_by_principal(self, app):
        # Given
        redactor = educational_factories.EducationalRedactorFactory(
            civility="M.",
            firstName="Jean",
            lastName="Doudou",
            email="jean.doux@example.com",
        )
        validated_eac_booking = bookings_factories.EducationalBookingFactory(
            dateCreated=datetime.utcnow() - timedelta(days=5),
            educationalBooking__educationalRedactor=redactor,
            educationalBooking__status=EducationalBookingStatus.USED_BY_INSTITUTE,
        )
        pro_user = users_factories.ProFactory()
        offers_factories.UserOffererFactory(
            user=pro_user, offerer=validated_eac_booking.stock.offer.venue.managingOfferer
        )
        url = f"/v2/bookings/token/{validated_eac_booking.token}"

        # When
        response = TestClient(app.test_client()).with_basic_auth(pro_user.email).get(url)

        # Then
        assert response.headers["Content-type"] == "application/json"
        assert response.status_code == 200
        assert response.json == {
            "bookingId": humanize(validated_eac_booking.id),
            "dateOfBirth": "",
            "datetime": format_into_utc_date(validated_eac_booking.stock.beginningDatetime),
            "ean13": "",
            "email": redactor.email,
            "formula": "PLACE",
            "isUsed": False,
            "offerId": validated_eac_booking.stock.offer.id,
            "offerName": validated_eac_booking.stock.offer.name,
            "offerType": "EVENEMENT",
            "phoneNumber": "",
            "price": float(validated_eac_booking.stock.price),
            "publicOfferId": humanize(validated_eac_booking.stock.offer.id),
            "quantity": validated_eac_booking.quantity,
            "theater": {},
            "userName": f"{redactor.firstName} {redactor.lastName}",
            "venueAddress": validated_eac_booking.stock.offer.venue.address,
            "venueDepartementCode": validated_eac_booking.stock.offer.venue.departementCode,
            "venueName": validated_eac_booking.stock.offer.venue.name,
        }

    def test_when_api_key_is_provided_and_rights_and_regular_offer(self, app):
        # Given
        user = users_factories.BeneficiaryFactory(email="user@example.com", publicName="John Doe")
        user2 = users_factories.UserFactory(email="user2@example.com", publicName="Jane Doe")
        offerer = create_offerer()
        user_offerer = create_user_offerer(user2, offerer)
        venue = create_venue(offerer)
        offer = create_offer_with_event_product(
            venue, event_name="Event Name", event_subcategory_id=subcategories.SEANCE_CINE.id
        )
        event_occurrence = create_event_occurrence(offer)
        stock = create_stock_from_event_occurrence(event_occurrence, price=0)
        booking = create_booking(user=user, stock=stock, venue=venue)
        repository.save(user_offerer, booking)
        ApiKeyFactory(offerer=offerer)
        user2ApiKey = "Bearer development_prefix_clearSecret"
        booking_token = booking.token.lower()
        url = f"/v2/bookings/token/{booking_token}"

        # When
        response = TestClient(app.test_client()).get(
            url, headers={"Authorization": user2ApiKey, "Origin": "http://localhost"}
        )

        # Then
        assert response.status_code == 200

    def test_when_user_has_rights_and_regular_offer_and_token_in_lower_case(self, app):
        # Given
        user = users_factories.BeneficiaryFactory(email="user@example.com", publicName="John Doe")
        admin_user = users_factories.AdminFactory(email="admin@example.com")
        offerer = create_offerer()
        user_offerer = create_user_offerer(admin_user, offerer)
        venue = create_venue(offerer)
        offer = create_offer_with_event_product(
            venue, event_name="Event Name", event_subcategory_id=subcategories.SEANCE_CINE.id
        )
        event_occurrence = create_event_occurrence(offer)
        stock = create_stock_from_event_occurrence(event_occurrence, price=0)
        booking = create_booking(user=user, stock=stock, venue=venue)
        repository.save(user_offerer, booking)
        booking_token = booking.token.lower()
        url = f"/v2/bookings/token/{booking_token}"

        # When
        response = TestClient(app.test_client()).with_basic_auth("admin@example.com").get(url)

        # Then
        assert response.status_code == 200

    def test_when_non_standard_origin_header(self, app):
        # Given
        user = users_factories.BeneficiaryFactory()
        admin_user = users_factories.AdminFactory(email="admin@example.com")
        offerer = create_offerer()
        user_offerer = create_user_offerer(admin_user, offerer)
        venue = create_venue(offerer)
        stock = create_stock_with_event_offer(
            offerer,
            venue,
            price=0,
            beginning_datetime=datetime.utcnow() + timedelta(hours=46),
            booking_limit_datetime=datetime.utcnow() + timedelta(hours=24),
        )
        booking = create_booking(user=user, stock=stock, venue=venue)
        repository.save(booking, user_offerer)
        url = f"/v2/bookings/token/{booking.token}"

        # When
        response = (
            TestClient(app.test_client())
            .with_basic_auth("admin@example.com")
            .get(url, headers={"origin": "http://random_header.fr"})
        )

        # Then
        assert response.status_code == 200


class Returns401Test:
    def test_when_user_not_logged_in_and_doesnt_give_api_key(self, app):
        # Given
        url = "/v2/bookings/token/MOCKED_TOKEN"

        # When
        response = TestClient(app.test_client()).get(url)

        # Then
        assert response.status_code == 401

    def test_when_user_not_logged_in_and_given_api_key_does_not_exist(self, app):
        # Given
        url = "/v2/bookings/token/FAKETOKEN"

        # When
        response = TestClient(app.test_client()).get(
            url, headers={"Authorization": "Bearer WrongApiKey1234567", "Origin": "http://localhost"}
        )

        # Then
        assert response.status_code == 401

    def test_when_user_not_logged_in_and_existing_api_key_given_with_no_bearer_prefix(self, app):
        # Given
        url = "/v2/bookings/token/FAKETOKEN"

        # When
        response = TestClient(app.test_client()).get(
            url, headers={"Authorization": "development_prefix_clearSecret", "Origin": "http://localhost"}
        )

        # Then
        assert response.status_code == 401


class Returns403Test:
    def test_when_user_doesnt_have_rights_and_token_exists(self, app):
        # Given
        user = users_factories.BeneficiaryFactory(email="user@example.com")
        querying_user = users_factories.UserFactory(email="querying@example.com")
        offerer = create_offerer()
        venue = create_venue(offerer)
        offer = create_offer_with_event_product(venue, event_name="Event Name")
        event_occurrence = create_event_occurrence(offer)
        stock = create_stock_from_event_occurrence(event_occurrence, price=0)
        booking = create_booking(user=user, stock=stock, venue=venue)
        repository.save(querying_user, booking)
        url = f"/v2/bookings/token/{booking.token}"

        # When
        response = TestClient(app.test_client()).with_basic_auth("querying@example.com").get(url)

        # Then
        assert response.status_code == 403
        assert response.json["user"] == ["Vous n'avez pas les droits suffisants pour valider cette contremarque."]

    def test_when_given_api_key_not_related_to_booking_offerer(self, app):
        # Given
        user = users_factories.BeneficiaryFactory(email="user@example.com")
        offerer2 = offers_factories.OffererFactory(siren="987654321")
        offer = offers_factories.EventOfferFactory(subcategoryId=subcategories.SEANCE_CINE.id)
        stock = offers_factories.EventStockFactory(offer=offer, price=0)
        booking = bookings_factories.BookingFactory(user=user, stock=stock)

        ApiKeyFactory(offerer=offerer2)
        user2ApiKey = "Bearer development_prefix_clearSecret"
        url = f"/v2/bookings/token/{booking.token}"

        # When
        response = TestClient(app.test_client()).get(
            url, headers={"Authorization": user2ApiKey, "Origin": "http://localhost"}
        )

        # Then
        assert response.status_code == 403
        assert response.json["user"] == ["Vous n'avez pas les droits suffisants pour valider cette contremarque."]

    @mock.patch("pcapi.core.bookings.validation.check_is_usable")
    def test_when_booking_not_confirmed(self, mocked_check_is_usable, app):
        # Given
        next_week = datetime.utcnow() + timedelta(weeks=1)
        unconfirmed_booking = bookings_factories.BookingFactory(stock__beginningDatetime=next_week)
        pro_user = users_factories.ProFactory(email="pro@example.com")
        offerer = unconfirmed_booking.stock.offer.venue.managingOfferer
        offers_factories.UserOffererFactory(user=pro_user, offerer=offerer)
        url = f"/v2/bookings/token/{unconfirmed_booking.token}"
        mocked_check_is_usable.side_effect = api_errors.ForbiddenError(errors={"booking": ["Not confirmed"]})

        # When
        response = TestClient(app.test_client()).with_basic_auth("pro@example.com").get(url)

        # Then
        assert response.status_code == 403
        assert response.json["booking"] == ["Not confirmed"]

    def test_when_booking_is_cancelled(self, app):
        # Given
        user = users_factories.BeneficiaryFactory(email="user@example.com")
        admin_user = users_factories.AdminFactory(email="admin@example.com")
        offerer = create_offerer()
        user_offerer = create_user_offerer(admin_user, offerer)
        venue = create_venue(offerer)
        stock = create_stock_with_thing_offer(offerer, venue, offer=None, price=0)
        booking = create_booking(user=user, stock=stock, is_cancelled=True, venue=venue)
        repository.save(admin_user, booking, user_offerer)
        ApiKeyFactory(offerer=offerer)
        user2ApiKey = "Bearer development_prefix_clearSecret"
        url = f"/v2/bookings/token/{booking.token}"

        # When
        response = TestClient(app.test_client()).get(
            url, headers={"Authorization": user2ApiKey, "Origin": "http://localhost"}
        )

        # Then
        assert response.status_code == 403
        assert response.json["booking"] == ["Cette réservation a été annulée"]

    def test_when_booking_is_refunded(self, app):
        # Given
        user = users_factories.BeneficiaryFactory(email="user@example.com")
        admin_user = users_factories.AdminFactory(email="admin@example.com")
        offerer = create_offerer()
        user_offerer = create_user_offerer(admin_user, offerer)
        venue = create_venue(offerer)
        stock = create_stock_with_thing_offer(offerer, venue, offer=None, price=0)
        booking = create_booking(user=user, stock=stock, is_used=True, venue=venue)
        payment = create_payment(booking=booking, offerer=offerer)
        repository.save(admin_user, payment, user_offerer)
        ApiKeyFactory(offerer=offerer)
        user2ApiKey = "Bearer development_prefix_clearSecret"
        url = f"/v2/bookings/token/{booking.token}"

        # When
        response = TestClient(app.test_client()).get(
            url, headers={"Authorization": user2ApiKey, "Origin": "http://localhost"}
        )

        # Then
        assert response.status_code == 403
        assert response.json["payment"] == ["Cette réservation a été remboursée"]

    def test_when_booking_is_educational_and_not_validated_by_principal_yet(self, app):
        # Given
        redactor = educational_factories.EducationalRedactorFactory(
            civility="M.",
            firstName="Jean",
            lastName="Doudou",
            email="jean.doux@example.com",
        )
        not_validated_eac_booking = bookings_factories.EducationalBookingFactory(
            dateCreated=datetime.utcnow() - timedelta(days=5),
            educationalBooking__educationalRedactor=redactor,
            educationalBooking__status=None,
        )
        pro_user = users_factories.ProFactory()
        offers_factories.UserOffererFactory(
            user=pro_user, offerer=not_validated_eac_booking.stock.offer.venue.managingOfferer
        )
        url = f"/v2/bookings/token/{not_validated_eac_booking.token}"

        # When
        response = TestClient(app.test_client()).with_basic_auth(pro_user.email).get(url)

        # Then
        assert response.status_code == 403
        assert (
            response.json["educationalBooking"]
            == "Cette réservation pour une offre éducationnelle n'est pas encore validée par le chef d'établissement"
        )

    def test_when_booking_is_educational_and_refused_by_principal(self, app):
        # Given
        redactor = educational_factories.EducationalRedactorFactory(
            civility="M.",
            firstName="Jean",
            lastName="Doudou",
            email="jean.doux@example.com",
        )
        refused_eac_booking = bookings_factories.EducationalBookingFactory(
            dateCreated=datetime.utcnow() - timedelta(days=5),
            educationalBooking__educationalRedactor=redactor,
            educationalBooking__status=EducationalBookingStatus.REFUSED,
        )
        pro_user = users_factories.ProFactory()
        offers_factories.UserOffererFactory(
            user=pro_user, offerer=refused_eac_booking.stock.offer.venue.managingOfferer
        )
        url = f"/v2/bookings/token/{refused_eac_booking.token}"

        # When
        response = TestClient(app.test_client()).with_basic_auth(pro_user.email).get(url)

        # Then
        assert response.status_code == 403
        assert (
            response.json["educationalBooking"]
            == "Cette réservation pour une offre éducationnelle a été refusée par le chef d'établissement"
        )


class Returns404Test:
    def test_when_booking_is_not_provided_at_all(self, app):
        # Given
        user = users_factories.BeneficiaryFactory(email="user@example.com")
        offerer = create_offerer()
        venue = create_venue(offerer)
        offer = create_offer_with_event_product(venue, event_name="Event Name")
        event_occurrence = create_event_occurrence(offer)
        stock = create_stock_from_event_occurrence(event_occurrence, price=0)
        booking = create_booking(user=user, stock=stock, venue=venue)
        repository.save(booking)
        url = "/v2/bookings/token/"

        # When
        response = TestClient(app.test_client()).get(url)

        # Then
        assert response.status_code == 404

    def test_when_token_user_has_rights_but_token_not_found(self, app):
        # Given
        admin_user = users_factories.AdminFactory(email="admin@example.com")
        repository.save(admin_user)
        url = "/v2/bookings/token/12345"

        # When
        response = TestClient(app.test_client()).with_basic_auth("admin@example.com").get(url)

        # Then
        assert response.status_code == 404
        assert response.json["global"] == ["Cette contremarque n'a pas été trouvée"]

    def test_when_user_has_api_key_but_token_not_found(self, app):
        # Given
        user = users_factories.BeneficiaryFactory(email="user@example.com")
        admin_user = users_factories.AdminFactory(email="admin@example.com")
        offerer = create_offerer()
        user_offerer = create_user_offerer(admin_user, offerer)
        venue = create_venue(offerer)
        offer = create_offer_with_event_product(venue, event_name="Event Name")
        event_occurrence = create_event_occurrence(offer)
        stock = create_stock_from_event_occurrence(event_occurrence, price=0)
        booking = create_booking(user=user, stock=stock, venue=venue)
        repository.save(admin_user, booking, user_offerer)
        ApiKeyFactory(offerer=offerer)
        user2ApiKey = "Bearer development_prefix_clearSecret"
        url = "/v2/bookings/token/12345"

        # When
        response = TestClient(app.test_client()).get(
            url, headers={"Authorization": user2ApiKey, "Origin": "http://localhost"}
        )

        # Then
        assert response.status_code == 404
        assert response.json["global"] == ["Cette contremarque n'a pas été trouvée"]


class Returns410Test:
    def test_when_booking_is_already_validated(self, app):
        # Given
        user = users_factories.BeneficiaryFactory(email="user@example.com")
        admin_user = users_factories.AdminFactory(email="admin@example.com")
        offerer = create_offerer()
        user_offerer = create_user_offerer(admin_user, offerer)
        venue = create_venue(offerer)
        stock = create_stock_with_thing_offer(offerer, venue, offer=None, price=0)
        booking = create_booking(user=user, stock=stock, is_used=True, venue=venue)
        repository.save(booking, user_offerer)
        ApiKeyFactory(offerer=offerer)
        user2ApiKey = "Bearer development_prefix_clearSecret"
        url = f"/v2/bookings/token/{booking.token}"

        # When
        response = TestClient(app.test_client()).get(
            url, headers={"Authorization": user2ApiKey, "Origin": "http://localhost"}
        )

        # Then
        assert response.status_code == 410
        assert response.json["booking"] == ["Cette réservation a déjà été validée"]
