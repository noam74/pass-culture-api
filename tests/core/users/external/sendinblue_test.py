from pcapi.core.users import testing
from pcapi.core.users.external.sendinblue import update_contact_attributes
from pcapi.core.users.factories import UserFactory


def test_update_contact_attributes():
    user = UserFactory()
    update_contact_attributes(user)

    assert testing.sendinblue_requests == [
        {
            "attributes": {"FIRSTNAME": "Jeanne", "IS_BENEFICIARY": True, "LASTNAME": "Doux"},
            "email": user.email,
        },
    ]
