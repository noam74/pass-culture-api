import pytest

from pcapi.model_creators.specific_creators import create_product_with_thing_type
from pcapi.models import ApiErrors
from pcapi.models import ThingType
from pcapi.repository import repository


def test_thing_error_when_thing_type_is_offlineOnly_but_has_url(app):
    # Given
    thing_product = create_product_with_thing_type(thing_type=ThingType.JEUX, url="http://mygame.fr/offre")

    # When
    with pytest.raises(ApiErrors) as errors:
        repository.save(thing_product)

    # Then
    assert errors.value.errors["url"] == ["Une offre de type Jeux (support physique) ne peut pas être numérique"]


def test_thing_offerType_returns_dict_matching_ThingType_enum():
    # given
    thing_product = create_product_with_thing_type(thing_type=ThingType.LIVRE_EDITION)
    expected_value = {
        "conditionalFields": ["author", "isbn"],
        "proLabel": "Livres papier ou numérique, abonnements lecture",
        "appLabel": "Livre ou carte lecture",
        "offlineOnly": False,
        "onlineOnly": False,
        "sublabel": "Lire",
        "description": "S’abonner à un quotidien d’actualité ?"
        " À un hebdomadaire humoristique ? "
        "À un mensuel dédié à la nature ? "
        "Acheter une BD ou un manga ? "
        "Ou tout simplement ce livre dont tout le monde parle ?",
        "value": "ThingType.LIVRE_EDITION",
        "type": "Thing",
        "isActive": True,
        "canExpire": True,
    }

    # when
    offer_type = thing_product.offerType

    # then
    assert offer_type == expected_value


def test_thing_offerType_returns_None_if_type_does_not_match_ThingType_enum():
    # given
    thing_product = create_product_with_thing_type(thing_type="")

    # when
    offer_type = thing_product.offerType

    # then
    assert offer_type == None
