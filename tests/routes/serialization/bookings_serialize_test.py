from datetime import datetime

import pytest

from pcapi.core.bookings.factories import BookingFactory
from pcapi.core.offers.factories import StockWithActivationCodesFactory
from pcapi.routes.serialization.bookings_serialize import serialize_booking_minimal
from pcapi.utils.human_ids import humanize


# FIXME: We already check (or should check) the JSON output of routes
# that use these serializers. These tests are probably not very useful
# and could be removed.


@pytest.mark.usefixtures("db_session")
class SerializeBookingMinimalTest:
    def test_should_return_booking_with_expected_information(self):
        # Given
        booking = BookingFactory(
            amount=1,
            quantity=1,
            token="GQTQR9",
            stock__price=10,
        )

        # When
        serialized = serialize_booking_minimal(booking)

        # Then
        assert serialized == {
            "amount": 1.0,
            "isCancelled": booking.isCancelled,
            "id": humanize(booking.id),
            "stockId": humanize(booking.stockId),
            "quantity": 1,
            "stock": {
                "price": 10,
            },
            "token": "GQTQR9",
            "completedUrl": None,
            "activationCode": None,
            "qrCode": booking.qrCode,
        }

    def test_should_return_booking_with_activation_code(self):
        # Given
        stocks = StockWithActivationCodesFactory(activationCodes__expirationDate=datetime(2030, 2, 5, 9, 0, 0))
        activation_code = stocks.activationCodes[0]
        booking = BookingFactory(amount=1, quantity=1, token="GQTQR9", stock__price=10, activationCode=activation_code)

        # When
        serialized = serialize_booking_minimal(booking)

        # Then
        assert serialized == {
            "amount": 1.0,
            "isCancelled": booking.isCancelled,
            "id": humanize(booking.id),
            "stockId": humanize(booking.stockId),
            "quantity": 1,
            "stock": {
                "price": 10,
            },
            "token": "GQTQR9",
            "completedUrl": None,
            "activationCode": {"code": activation_code.code, "expirationDate": activation_code.expirationDate},
            "qrCode": booking.qrCode,
        }
