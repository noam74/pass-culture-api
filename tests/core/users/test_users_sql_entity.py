from datetime import datetime

from freezegun import freeze_time
import pytest

import pcapi.core.bookings.factories as bookings_factories
import pcapi.core.offers.factories as offers_factories
import pcapi.core.payments.factories as payments_factories
from pcapi.core.users import factories
from pcapi.core.users.factories import UserFactory
from pcapi.model_creators.generic_creators import create_offerer
from pcapi.model_creators.generic_creators import create_user
from pcapi.model_creators.generic_creators import create_user_offerer
from pcapi.model_creators.generic_creators import create_venue
from pcapi.models import ApiErrors
from pcapi.repository import repository


def test_cannot_create_admin_that_can_book(app):
    # Given
    user = create_user(is_beneficiary=True, is_admin=True)

    # When
    with pytest.raises(ApiErrors):
        repository.save(user)


class HasAccessTest:
    def test_does_not_have_access_if_not_attached(self):
        offerer = offers_factories.OffererFactory()
        user = factories.UserFactory()

        assert not user.has_access(offerer.id)

    def test_does_not_have_access_if_not_validated(self, app):
        user_offerer = offers_factories.UserOffererFactory(validationToken="token")
        offerer = user_offerer.offerer
        user = user_offerer.user

        assert not user.has_access(offerer.id)

    def test_has_access(self):
        user_offerer = offers_factories.UserOffererFactory()
        offerer = user_offerer.offerer
        user = user_offerer.user

        assert user.has_access(offerer.id)

    def test_has_access_if_admin(self):
        # given
        offerer = offers_factories.OffererFactory()
        admin = factories.UserFactory(isAdmin=True)

        assert admin.has_access(offerer.id)


class WalletBalanceTest:
    def test_balance_is_0_with_no_deposits_and_no_bookings(self):
        # given
        user = factories.UserFactory()
        repository.delete(user.deposit)

        # then
        assert user.wallet_balance == 0
        assert user.real_wallet_balance == 0

    def test_balance_is_the_sum_of_deposits_if_no_bookings(self):
        # given
        user = factories.UserFactory(deposit__version=1)
        payments_factories.DepositFactory(user=user, version=1)

        # then
        assert user.wallet_balance == 500 + 500
        assert user.real_wallet_balance == 500 + 500

    def test_balance_count_non_expired_deposits(self):
        # given
        user = factories.UserFactory(deposit__version=1, deposit__expirationDate=None)

        # then
        assert user.wallet_balance == 500
        assert user.real_wallet_balance == 500

    def test_balance_ignores_expired_deposits(self):
        # given
        user = factories.UserFactory(deposit__version=1, deposit__expirationDate=datetime(2000, 1, 1))

        # then
        assert user.wallet_balance == 0
        assert user.real_wallet_balance == 0

    def test_balance(self):
        # given
        user = factories.UserFactory(deposit__version=1)
        bookings_factories.BookingFactory(user=user, isUsed=True, quantity=1, amount=10)
        bookings_factories.BookingFactory(user=user, isUsed=True, quantity=2, amount=20)
        bookings_factories.BookingFactory(user=user, isUsed=False, quantity=3, amount=30)
        bookings_factories.BookingFactory(user=user, isCancelled=True, quantity=4, amount=40)

        # then
        assert user.wallet_balance == 500 - (10 + 2 * 20 + 3 * 30)
        assert user.real_wallet_balance == 500 - (10 + 2 * 20)

    def test_real_balance_with_only_used_bookings(self):
        # given
        user = factories.UserFactory(deposit__version=1)
        bookings_factories.BookingFactory(user=user, isUsed=False, quantity=1, amount=30)

        # then
        assert user.wallet_balance == 500 - 30
        assert user.real_wallet_balance == 500

    def test_balance_should_not_be_negative(self):
        # given
        user = factories.UserFactory(deposit__version=1)
        bookings_factories.BookingFactory(user=user, isUsed=True, quantity=1, amount=10)
        deposit = user.deposit
        deposit.expirationDate = datetime(2000, 1, 1)

        # then
        assert user.wallet_balance == 0
        assert user.real_wallet_balance == 0


class HasPhysicalVenuesTest:
    def test_webapp_user_has_no_venue(self, app):
        # given
        user = create_user()

        # when
        repository.save(user)

        # then
        assert user.hasPhysicalVenues is False

    def test_pro_user_has_one_digital_venue_by_default(self, app):
        # given
        user = create_user()
        offerer = create_offerer()
        user_offerer = create_user_offerer(user, offerer)
        offerer_venue = create_venue(offerer, is_virtual=True, siret=None)

        # when
        repository.save(offerer_venue, user_offerer)

        # then
        assert user.hasPhysicalVenues is False

    def test_pro_user_has_one_digital_venue_and_a_physical_venue(self, app):
        # given
        user = create_user()
        offerer = create_offerer()
        user_offerer = create_user_offerer(user, offerer)
        offerer_virtual_venue = create_venue(offerer, is_virtual=True, siret=None)
        offerer_physical_venue = create_venue(offerer)
        repository.save(offerer_virtual_venue, offerer_physical_venue, user_offerer)

        # then
        assert user.hasPhysicalVenues is True


class needsToSeeTutorialsTest:
    def test_beneficiary_has_to_see_tutorials_when_not_already_seen(self, app):
        # given
        user = create_user(is_beneficiary=True, has_seen_tutorials=False)
        # when
        repository.save(user)
        # then
        assert user.needsToSeeTutorials is True

    def test_beneficiary_has_not_to_see_tutorials_when_already_seen(self, app):
        # given
        user = create_user(is_beneficiary=True, has_seen_tutorials=True)
        # when
        repository.save(user)
        # then
        assert user.needsToSeeTutorials is False

    def test_pro_user_has_not_to_see_tutorials_when_already_seen(self, app):
        # given
        user = create_user(is_beneficiary=False)
        # when
        repository.save(user)
        # then
        assert user.needsToSeeTutorials is False


class CalculateAgeTest:
    @freeze_time("2018-06-01")
    def test_user_age(self):
        assert create_user(date_of_birth=None).age is None
        assert create_user(date_of_birth=datetime(2000, 6, 1, 5, 1)).age == 18  # happy birthday
        assert create_user(date_of_birth=datetime(1999, 7, 1)).age == 18
        assert create_user(date_of_birth=datetime(2000, 7, 1)).age == 17
        assert create_user(date_of_birth=datetime(1999, 5, 1)).age == 19

    def test_eligibility_start_end_datetime(self):
        assert create_user(date_of_birth=None).eligibility_start_datetime is None
        assert create_user(date_of_birth=datetime(2000, 6, 1, 5, 1)).eligibility_start_datetime == datetime(
            2018, 6, 1, 0, 0
        )

        assert create_user(date_of_birth=None).eligibility_end_datetime is None
        assert create_user(date_of_birth=datetime(2000, 6, 1, 5, 1)).eligibility_end_datetime == datetime(
            2019, 6, 1, 0, 0
        )


class DepositVersionTest:
    def test_return_the_deposit(self):
        # given
        user = UserFactory(deposit__version=1)

        # then
        assert user.deposit_version == 1

    def test_when_no_deposit(self):
        # given
        user = UserFactory()
        repository.delete(*user.deposits)

        # then
        assert user.deposit_version == None


class NotificationSubscriptionsTest:
    def test_notification_subscriptions(self):
        user = UserFactory(notificationSubscriptions={"marketing_push": False})

        assert not user.get_notification_subscriptions().marketing_push

    def test_void_notification_subscriptions(self):
        user = UserFactory()
        assert user.notificationSubscriptions == {"marketing_push": True, "marketing_email": True}

        assert user.get_notification_subscriptions().marketing_push
