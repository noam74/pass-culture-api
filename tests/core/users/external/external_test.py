from pcapi.core.users import testing
from pcapi.core.users.external import update_external_user
from pcapi.core.users.factories import UserFactory


def test_update_external_user():
    user = UserFactory()
    update_external_user(user)

    assert len(testing.sendinblue_requests) == 1
