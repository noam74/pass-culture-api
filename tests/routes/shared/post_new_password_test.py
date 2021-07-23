from datetime import datetime
from datetime import timedelta

from pcapi.core.users import factories as users_factories
from pcapi.core.users.models import TokenType

from tests.conftest import TestClient


def test_change_password(app):
    user = users_factories.UserFactory()
    token = users_factories.TokenFactory(user=user, type=TokenType.RESET_PASSWORD)
    data = {"token": token.value, "newPassword": "N3W_p4ssw0rd"}

    client = TestClient(app.test_client())
    response = client.post("/users/new-password", json=data)

    assert response.status_code == 204
    assert user.checkPassword("N3W_p4ssw0rd")
    assert len(user.tokens) == 0


def test_change_password_with_legacy_reset_token(app):
    user = users_factories.UserFactory(
        resetPasswordToken="TOKEN",
        resetPasswordTokenValidityLimit=datetime.utcnow() + timedelta(hours=24),
    )
    data = {"token": "TOKEN", "newPassword": "N3W_p4ssw0rd"}

    client = TestClient(app.test_client())
    response = client.post("/users/new-password", json=data)

    assert response.status_code == 204
    assert user.checkPassword("N3W_p4ssw0rd")
    assert len(user.tokens) == 0


def test_fail_if_token_has_expired(app):
    user = users_factories.UserFactory(password="Old_P4ssword")
    token = users_factories.TokenFactory(
        userId=user.id,
        type=TokenType.RESET_PASSWORD,
        expirationDate=datetime.utcnow() - timedelta(hours=24),
    )
    data = {"token": token.value, "newPassword": "N3W_p4ssw0rd"}

    client = TestClient(app.test_client())
    response = client.post("/users/new-password", json=data)

    assert response.status_code == 400
    assert response.json["token"] == ["Votre lien de changement de mot de passe est invalide."]
    assert user.checkPassword("Old_P4ssword")


def test_fail_if_token_has_expired_with_legacy_reset_token(app):
    user = users_factories.UserFactory(
        password="Old_P4ssword",
        resetPasswordToken="TOKEN",
        resetPasswordTokenValidityLimit=datetime.utcnow() - timedelta(hours=24),
    )
    data = {"token": "TOKEN", "newPassword": "N3W_p4ssw0rd"}

    client = TestClient(app.test_client())
    response = client.post("/users/new-password", json=data)

    assert response.status_code == 400
    assert response.json["token"] == ["Votre lien de changement de mot de passe est invalide."]
    assert user.checkPassword("Old_P4ssword")


def test_fail_if_token_is_unknown(app):
    users_factories.UserFactory(resetPasswordToken="TOKEN")
    data = {"token": "OTHER TOKEN", "newPassword": "N3W_p4ssw0rd"}

    client = TestClient(app.test_client())
    response = client.post("/users/new-password", json=data)

    assert response.status_code == 400
    assert response.json["token"] == ["Votre lien de changement de mot de passe est invalide."]


def test_fail_if_token_is_missing(app):
    data = {"newPassword": "N3W_p4ssw0rd"}

    client = TestClient(app.test_client())
    response = client.post("/users/new-password", json=data)

    assert response.status_code == 400
    assert response.json["token"] == ["Votre lien de changement de mot de passe est invalide."]


def test_fail_if_new_password_is_missing(app):
    data = {"token": "KL89PBNG51"}

    client = app.test_client()
    response = TestClient(client).post("/users/new-password", json=data)

    assert response.status_code == 400
    assert response.json["newPassword"] == ["Vous devez renseigner un nouveau mot de passe."]


def test_fail_if_new_password_is_not_strong_enough(app):
    data = {"token": "TOKEN", "newPassword": "weak_password"}

    client = TestClient(app.test_client())
    response = client.post("/users/new-password", json=data)

    assert response.status_code == 400
    assert response.json["newPassword"] == [
        "Ton mot de passe doit contenir au moins :\n"
        "- 12 caractères\n"
        "- Un chiffre\n"
        "- Une majuscule et une minuscule\n"
        "- Un caractère spécial"
    ]
