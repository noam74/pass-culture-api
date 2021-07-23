from datetime import date
from datetime import timedelta
from unittest import mock

from pcapi.core.bookings.factories import BookingFactory
from pcapi.core.offers.factories import ProductFactory
from pcapi.models import offer_type
from pcapi.repository import repository
from pcapi.scripts.booking.notify_soon_to_be_expired_bookings import notify_users_of_soon_to_be_expired_bookings


class NotifyUsersOfSoonToBeExpiredBookingsTest:
    @mock.patch(
        "pcapi.scripts.booking.notify_soon_to_be_expired_bookings.send_soon_to_be_expired_bookings_recap_email_to_beneficiary"
    )
    def should_call_email_service_for_bookings_which_will_expire_in_7_days(self, mocked_email_recap, app) -> None:
        # Given
        now = date.today()
        booking_date_23_days_ago = now - timedelta(days=23)
        booking_date_22_days_ago = now - timedelta(days=22)

        dvd = ProductFactory(type=str(offer_type.ThingType.AUDIOVISUEL))
        expire_in_7_days_dvd_booking = BookingFactory(
            stock__offer__product=dvd,
            dateCreated=booking_date_23_days_ago,
            isCancelled=False,
        )
        non_expired_cd = ProductFactory(type=str(offer_type.ThingType.MUSIQUE))
        dont_expire_in_7_days_cd_booking = BookingFactory(
            stock__offer__product=non_expired_cd,
            dateCreated=booking_date_22_days_ago,
            isCancelled=False,
        )
        repository.save(dont_expire_in_7_days_cd_booking)

        # When
        notify_users_of_soon_to_be_expired_bookings()

        # Then
        mocked_email_recap.assert_called_once_with(expire_in_7_days_dvd_booking.user, [expire_in_7_days_dvd_booking])
