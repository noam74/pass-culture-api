from datetime import datetime, timedelta

from pytest import fixture

from domain.booking_recap.bookings_recap_paginated import BookingsRecapPaginated
from routes.serialization.bookings_recap_serialize import serialize_bookings_recap_paginated
from tests.domain_creators.generic_creators import create_domain_thing_booking_recap, create_domain_event_booking_recap
from utils.date import format_into_timezoned_date
from utils.human_ids import humanize


class SerializeBookingRecapTest:
    def test_should_return_json_with_all_parameters_for_thing_stock(self, app: fixture) -> None:
        # Given
        booking_date = datetime(2020, 1, 1, 10, 0, 0)
        thing_booking_recap = create_domain_thing_booking_recap(
            offer_identifier=1,
            offer_name="Fondation",
            beneficiary_firstname="Hari",
            beneficiary_lastname="Seldon",
            beneficiary_email="hari.seldon@example.com",
            booking_date=booking_date,
            booking_token="FOND",
            booking_is_used=False,
            booking_amount=18
        )
        thing_booking_recap_2 = create_domain_thing_booking_recap(
            offer_identifier=2,
            offer_name="Fondation",
            beneficiary_firstname="Golan",
            beneficiary_lastname="Trevize",
            beneficiary_email="golan.trevize@example.com",
            booking_date=booking_date,
            booking_token="FOND",
            booking_is_duo=True,
        )
        bookings_recap = [
            thing_booking_recap,
            thing_booking_recap_2
        ]
        bookings_recap_paginated_response = BookingsRecapPaginated(
            bookings_recap=list(bookings_recap),
            page=0,
            pages=1,
            total=2
        )

        # When
        result = serialize_bookings_recap_paginated(bookings_recap_paginated_response)

        # Then
        expected_bookings_recap = [
            {
                "stock": {
                    "type": "thing",
                    "offer_name": "Fondation",
                    "offer_identifier": humanize(thing_booking_recap.offer_identifier),
                },
                "beneficiary": {
                    "lastname": "Seldon",
                    "firstname": "Hari",
                    "email": "hari.seldon@example.com",
                },
                "booking_date": format_into_timezoned_date(booking_date),
                "booking_token": None,
                "booking_status": "booked",
                "booking_is_duo": False,
                'booking_status_history': [
                    {
                        'status': 'booked',
                        'date': '2020-01-01T10:00:00',
                    },
                ],
                'booking_amount': 18,
                "venue": {
                    "identifier": "AE",
                    "name": "Librairie Kléber"
                }
            },
            {
                "stock": {
                    "type": "thing",
                    "offer_name": "Fondation",
                    "offer_identifier": humanize(thing_booking_recap_2.offer_identifier),
                },
                "beneficiary": {
                    "lastname": "Trevize",
                    "firstname": "Golan",
                    "email": "golan.trevize@example.com",
                },
                "booking_date": format_into_timezoned_date(booking_date),
                "booking_token": None,
                "booking_status": "booked",
                "booking_is_duo": True,
                'booking_status_history': [
                    {
                        'status': 'booked',
                        'date': '2020-01-01T10:00:00',
                    },
                ],
                'booking_amount': 0,
                "venue": {
                    "identifier": "AE",
                    "name": "Librairie Kléber"
                }
            }
        ]
        assert result['bookings_recap'] == expected_bookings_recap
        assert result['page'] == 0
        assert result['pages'] == 1
        assert result['total'] == 2

    def test_should_return_json_with_event_date_additional_parameter_for_event_stock(self, app: fixture) -> None:
        # Given
        booking_date = datetime(2020, 1, 1, 10, 0, 0)
        day_after_booking_date = booking_date + timedelta(days=1)
        event_booking_recap = create_domain_event_booking_recap(offer_name="Cirque du soleil",
                                                                beneficiary_firstname="Hari",
                                                                beneficiary_lastname="Seldon",
                                                                beneficiary_email="hari.seldon@example.com",
                                                                booking_date=booking_date, booking_token="SOLEIL",
                                                                event_beginning_datetime=day_after_booking_date,
                                                                )
        bookings_recap = [event_booking_recap]
        bookings_recap_paginated_response = BookingsRecapPaginated(
            bookings_recap=list(bookings_recap),
            page=0,
            pages=1,
            total=2
        )

        # When
        results = serialize_bookings_recap_paginated(bookings_recap_paginated_response)

        # Then
        expected_response = [
            {
                "stock": {
                    "type": "event",
                    "offer_name": "Cirque du soleil",
                    "offer_identifier": humanize(event_booking_recap.offer_identifier),
                    "event_beginning_datetime": format_into_timezoned_date(day_after_booking_date),
                },
                "beneficiary": {
                    "lastname": "Seldon",
                    "firstname": "Hari",
                    "email": "hari.seldon@example.com",
                },
                "booking_date": format_into_timezoned_date(booking_date),
                "booking_token": "SOLEIL",
                "booking_status": "booked",
                "booking_is_duo": False,
                'booking_status_history': [
                    {
                        'status': 'booked',
                        'date': '2020-01-01T10:00:00',
                    },
                ],
                'booking_amount': 0,
                "venue": {
                    "identifier": "AE",
                    "name": "Librairie Kléber"
                }
            },
        ]
        assert results['bookings_recap'] == expected_response
        assert results['page'] == 0
        assert results['pages'] == 1
        assert results['total'] == 2

    def test_should_return_json_with_offer_isbn_additional_parameter_for_thing_stock(self, app: fixture) -> None:
        # Given
        booking_date = datetime(2020, 1, 1, 10, 0, 0)
        thing_booking_recap = create_domain_thing_booking_recap(offer_identifier=1, offer_name="Martine a la playa",
                                                                offer_isbn='987654345678', beneficiary_firstname="Hari",
                                                                beneficiary_lastname="Seldon",
                                                                beneficiary_email="hari.seldon@example.com",
                                                                booking_date=booking_date, booking_token="LUNE")
        bookings_recap = [thing_booking_recap]
        bookings_recap_paginated_response = BookingsRecapPaginated(
            bookings_recap=list(bookings_recap),
            page=0,
            pages=1,
            total=2
        )

        # When
        results = serialize_bookings_recap_paginated(bookings_recap_paginated_response)

        # Then
        expected_response = [
            {
                "stock": {
                    "type": "book",
                    "offer_name": "Martine a la playa",
                    "offer_identifier": humanize(thing_booking_recap.offer_identifier),
                    "offer_isbn": '987654345678',
                },
                "beneficiary": {
                    "lastname": "Seldon",
                    "firstname": "Hari",
                    "email": "hari.seldon@example.com",
                },
                "booking_date": format_into_timezoned_date(booking_date),
                "booking_token": None,
                "booking_status": "booked",
                "booking_is_duo": False,
                'booking_amount': 0,
                'booking_status_history': [
                    {
                        'status': 'booked',
                        'date': '2020-01-01T10:00:00',
                    },
                ],
                "venue": {
                    "identifier": "AE",
                    "name": "Librairie Kléber"
                }
            },
        ]
        assert results['bookings_recap'] == expected_response
        assert results['page'] == 0
        assert results['pages'] == 1
        assert results['total'] == 2


class SerializeBookingRecapHistoryTest:
    def test_should_return_booking_recap_history_with_cancellation_date_when_cancelled(self, app: fixture) -> None:
        # Given
        booking_date = datetime(2020, 1, 1, 10, 0, 0)
        bookings_recap = [
            create_domain_thing_booking_recap(
                offer_name="Martine a la playa",
                offer_isbn='987654345678',
                beneficiary_firstname="Hari",
                beneficiary_lastname="Seldon",
                beneficiary_email="hari.seldon@example.com",
                booking_date=booking_date,
                booking_token="LUNE",
                booking_is_cancelled=True,
                cancellation_date=datetime(2020, 4, 3, 10, 0, 0)
            )
        ]
        bookings_recap_paginated_response = BookingsRecapPaginated(
            bookings_recap=list(bookings_recap),
            page=0,
            pages=1,
            total=2
        )

        # When
        results = serialize_bookings_recap_paginated(bookings_recap_paginated_response)

        # Then
        expected_booking_recap_history = [
            {
                'status': 'booked',
                'date': '2020-01-01T10:00:00',
            },
            {
                'status': 'cancelled',
                'date': '2020-04-03T10:00:00',
            }
        ]
        assert results['bookings_recap'][0]['booking_status_history'] == expected_booking_recap_history

    def test_should_return_booking_recap_history_with_reimbursed_and_used_dated_when_reimbursed(self,
                                                                                                app: fixture) -> None:
        # Given
        booking_date = datetime(2020, 1, 1, 10, 0, 0)
        bookings_recap = [
            create_domain_thing_booking_recap(
                offer_name="Martine a la playa",
                offer_isbn='987654345678',
                beneficiary_firstname="Hari",
                beneficiary_lastname="Seldon",
                beneficiary_email="hari.seldon@example.com",
                booking_date=booking_date,
                booking_token="LUNE",
                booking_is_used=True,
                booking_is_reimbursed=True,
                payment_date=datetime(2020, 5, 3, 10, 0),
                date_used=datetime(2020, 4, 3, 10, 0)
            )
        ]
        bookings_recap_paginated_response = BookingsRecapPaginated(
            bookings_recap=list(bookings_recap),
            page=0,
            pages=1,
            total=2
        )

        # When
        results = serialize_bookings_recap_paginated(bookings_recap_paginated_response)

        # Then
        expected_booking_recap_history = [
            {
                'status': 'booked',
                'date': '2020-01-01T10:00:00',
            },
            {
                'status': 'validated',
                'date': '2020-04-03T10:00:00',
            },
            {
                'status': 'reimbursed',
                'date': '2020-05-03T10:00:00',
            }
        ]
        assert results['bookings_recap'][0]['booking_status_history'] == expected_booking_recap_history

    def test_should_return_booking_recap_history_with_date_used_when_used(self, app: fixture) -> None:
        # Given
        booking_date = datetime(2020, 1, 1, 10, 0, 0)
        bookings_recap = [
            create_domain_thing_booking_recap(
                offer_name="Martine a la playa",
                offer_isbn='987654345678',
                beneficiary_firstname="Hari",
                beneficiary_lastname="Seldon",
                beneficiary_email="hari.seldon@example.com",
                booking_date=booking_date,
                booking_token="LUNE",
                booking_is_used=True,
                date_used=datetime(2020, 4, 3, 10, 0)
            )
        ]
        bookings_recap_paginated_response = BookingsRecapPaginated(
            bookings_recap=list(bookings_recap),
            page=0,
            pages=1,
            total=2
        )

        # When
        results = serialize_bookings_recap_paginated(bookings_recap_paginated_response)

        # Then
        expected_booking_recap_history = [
            {
                'status': 'booked',
                'date': '2020-01-01T10:00:00',
            },
            {
                'status': 'validated',
                'date': '2020-04-03T10:00:00',
            }
        ]
        assert results['bookings_recap'][0]['booking_status_history'] == expected_booking_recap_history

    def test_should_return_booking_recap_history_with_only_booking_date_when_just_booked(self, app: fixture) -> None:
        # Given
        booking_date = datetime(2020, 1, 1, 10, 0, 0)
        bookings_recap = [
            create_domain_thing_booking_recap(
                offer_name="Martine a la playa",
                offer_isbn='987654345678',
                beneficiary_firstname="Hari",
                beneficiary_lastname="Seldon",
                beneficiary_email="hari.seldon@example.com",
                booking_date=booking_date,
                booking_token="LUNE"
            )
        ]
        bookings_recap_paginated_response = BookingsRecapPaginated(
            bookings_recap=list(bookings_recap),
            page=0,
            pages=1,
            total=2
        )

        # When
        results = serialize_bookings_recap_paginated(bookings_recap_paginated_response)

        # Then
        expected_booking_recap_history = [
            {
                'status': 'booked',
                'date': '2020-01-01T10:00:00',
            },
        ]
        assert results['bookings_recap'][0]['booking_status_history'] == expected_booking_recap_history
