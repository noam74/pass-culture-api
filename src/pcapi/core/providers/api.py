from datetime import datetime
import logging
from typing import Iterable
from typing import Optional
from typing import Union

from pcapi.core import search
from pcapi.core.offerers.models import Venue
from pcapi.core.offers.models import Offer
from pcapi.core.offers.models import Stock
from pcapi.core.offers.repository import get_offers_map_by_id_at_providers
from pcapi.core.offers.repository import get_products_map_by_id_at_providers
from pcapi.core.offers.repository import get_stocks_by_id_at_providers
from pcapi.core.providers.exceptions import NoSiretSpecified
from pcapi.core.providers.exceptions import ProviderNotFound
from pcapi.core.providers.exceptions import ProviderWithoutApiImplementation
from pcapi.core.providers.exceptions import VenueNotFound
from pcapi.core.providers.exceptions import VenueSiretNotRegistered
from pcapi.core.providers.models import AllocineVenueProvider
from pcapi.core.providers.models import Provider
from pcapi.core.providers.models import VenueProvider
from pcapi.core.providers.models import VenueProviderCreationPayload
from pcapi.core.providers.repository import get_provider_enabled_for_pro_by_id
from pcapi.domain.price_rule import PriceRule
from pcapi.models import Product
from pcapi.models.db import db
from pcapi.repository import repository
from pcapi.repository.venue_queries import find_by_id
from pcapi.routes.serialization.venue_provider_serialize import PostVenueProviderBody
from pcapi.use_cases.connect_venue_to_allocine import connect_venue_to_allocine
from pcapi.validation.models.entity_validator import validate


logger = logging.getLogger(__name__)


def create_venue_provider(
    provider_id: int, venue_id: int, payload: VenueProviderCreationPayload = VenueProviderCreationPayload()
) -> VenueProvider:
    provider = get_provider_enabled_for_pro_by_id(provider_id)
    if not provider:
        raise ProviderNotFound()

    venue = find_by_id(venue_id)

    if not venue:
        raise VenueNotFound()

    if provider.localClass == "AllocineStocks":  # type: ignore
        new_venue_provider = connect_venue_to_allocine(venue, provider_id, payload)
    else:
        new_venue_provider = connect_venue_to_provider(
            venue, provider, payload.venueIdAtOfferProvider  # type: ignore[arg-type]
        )

    return new_venue_provider


def change_venue_provider(
    venue_provider: VenueProvider, new_provider_id: int, venueIdAtOfferProvider: str = None
) -> VenueProvider:
    new_provider = get_provider_enabled_for_pro_by_id(new_provider_id)
    if not new_provider:
        raise ProviderNotFound()

    id_at_provider = venueIdAtOfferProvider or venue_provider.venue.siret

    _check_provider_can_be_connected(new_provider, id_at_provider)

    venue_provider.provider = new_provider
    venue_provider.venueIdAtOfferProvider = id_at_provider

    repository.save(venue_provider)
    return venue_provider


def update_allocine_venue_provider(
    allocine_venue_provider: AllocineVenueProvider, venue_provider_payload: PostVenueProviderBody
) -> AllocineVenueProvider:
    allocine_venue_provider.quantity = venue_provider_payload.quantity
    allocine_venue_provider.isDuo = venue_provider_payload.isDuo
    for price_rule in allocine_venue_provider.priceRules:
        # PriceRule.default is the only existing value at this time
        # could need to be tweaked in the future
        if price_rule.priceRule == PriceRule.default:
            price_rule.price = venue_provider_payload.price

    repository.save(allocine_venue_provider, *allocine_venue_provider.priceRules)

    return allocine_venue_provider


ERROR_CODE_PROVIDER_NOT_SUPPORTED = 400
ERROR_CODE_SIRET_NOT_SUPPORTED = 422


def connect_venue_to_provider(venue: Venue, provider: Provider, venueIdAtOfferProvider: str = None) -> VenueProvider:
    id_at_provider = venueIdAtOfferProvider or venue.siret

    _check_provider_can_be_connected(provider, id_at_provider)

    venue_provider = VenueProvider()
    venue_provider.venue = venue
    venue_provider.provider = provider
    venue_provider.venueIdAtOfferProvider = id_at_provider

    repository.save(venue_provider)
    return venue_provider


def _check_provider_can_be_connected(provider: Provider, id_at_provider: Optional[str]) -> None:
    if not id_at_provider:
        raise NoSiretSpecified()

    if not provider.implements_provider_api:
        raise ProviderWithoutApiImplementation()

    if not _siret_can_be_synchronized(id_at_provider, provider):
        raise VenueSiretNotRegistered(provider.name, id_at_provider)
    return


def _siret_can_be_synchronized(
    siret: str,
    provider: Provider,
) -> bool:
    if not siret:
        return False

    if provider.implements_provider_api:
        provider_api = provider.getProviderAPI()
        return provider_api.is_siret_registered(siret)

    return False


def synchronize_stocks(
    stock_details: Iterable[dict], venue: Venue, provider_id: Optional[int] = None
) -> dict[str, int]:
    products_provider_references = [stock_detail["products_provider_reference"] for stock_detail in stock_details]
    products_by_provider_reference = get_products_map_by_id_at_providers(products_provider_references)

    stock_details = [
        stock for stock in stock_details if stock["products_provider_reference"] in products_by_provider_reference
    ]

    offers_provider_references = [stock_detail["offers_provider_reference"] for stock_detail in stock_details]
    offers_by_provider_reference = get_offers_map_by_id_at_providers(offers_provider_references)

    offers_update_mapping = _get_offers_update_mapping(offers_by_provider_reference.values(), provider_id)
    db.session.bulk_update_mappings(Offer, offers_update_mapping)

    new_offers = _build_new_offers_from_stock_details(
        stock_details, offers_by_provider_reference, products_by_provider_reference, venue, provider_id
    )
    new_offers_references = [new_offer.idAtProviders for new_offer in new_offers]

    db.session.bulk_save_objects(new_offers)

    new_offers_by_provider_reference = get_offers_map_by_id_at_providers(new_offers_references)
    offers_by_provider_reference = {**offers_by_provider_reference, **new_offers_by_provider_reference}

    stocks_provider_references = [stock["stocks_provider_reference"] for stock in stock_details]
    stocks_by_provider_reference = get_stocks_by_id_at_providers(stocks_provider_references)
    update_stock_mapping, new_stocks, offer_ids = _get_stocks_to_upsert(
        stock_details,
        stocks_by_provider_reference,
        offers_by_provider_reference,
        products_by_provider_reference,
        provider_id,
    )

    db.session.bulk_save_objects(new_stocks)
    db.session.bulk_update_mappings(Stock, update_stock_mapping)

    db.session.commit()

    search.async_index_offer_ids(offer_ids)

    return {"new_offers": len(new_offers), "new_stocks": len(new_stocks), "updated_stocks": len(update_stock_mapping)}


def _get_offers_update_mapping(offer_id_list: Iterable[int], provider_id: Optional[int]) -> list[dict]:
    return [{"id": offer_id, "lastProviderId": provider_id} for offer_id in offer_id_list]


def _build_new_offers_from_stock_details(
    stock_details: list,
    existing_offers_by_provider_reference: dict[str, int],
    products_by_provider_reference: dict[str, Product],
    venue: Venue,
    provider_id: Optional[int],
) -> list[Offer]:
    new_offers = []
    for stock_detail in stock_details:
        if stock_detail["offers_provider_reference"] in existing_offers_by_provider_reference:
            continue
        if not stock_detail["available_quantity"]:
            continue

        product = products_by_provider_reference[stock_detail["products_provider_reference"]]
        offer = _build_new_offer(
            venue,
            product,
            id_at_providers=stock_detail["offers_provider_reference"],
            id_at_provider=stock_detail["products_provider_reference"],
            provider_id=provider_id,
        )

        if not _validate_stock_or_offer(offer):
            continue

        new_offers.append(offer)

    return new_offers


def _get_stocks_to_upsert(
    stock_details: list[dict],
    stocks_by_provider_reference: dict[str, dict],
    offers_by_provider_reference: dict[str, int],
    products_by_provider_reference: dict[str, Product],
    provider_id: Optional[int],
) -> tuple[list[dict], list[Stock], set[int]]:
    update_stock_mapping = []
    new_stocks = []
    offer_ids = set()

    for stock_detail in stock_details:
        stock_provider_reference = stock_detail["stocks_provider_reference"]
        product = products_by_provider_reference[stock_detail["products_provider_reference"]]
        book_price = stock_detail.get("price") or float(product.extraData["prix_livre"])
        if stock_provider_reference in stocks_by_provider_reference:
            stock = stocks_by_provider_reference[stock_provider_reference]

            # FIXME (dbaty, 2021-05-18): analyze logs to see if the
            # provider sometimes stops sending a price after having
            # sent a specific price before. Should we keep the
            # possibly specific price that we have received before? Or
            # should we override with the (generic) product price?
            if not stock_detail.get("price") and float(stock["price"]) != book_price:
                logger.warning(
                    "Stock specific price has been overriden by product price because provider price is missing",
                    extra={
                        "stock": stock["id"],
                        "previous_stock_price": float(stock["price"]),
                        "new_price": book_price,
                    },
                )

            update_stock_mapping.append(
                {
                    "id": stock["id"],
                    "quantity": stock_detail["available_quantity"] + stock["booking_quantity"],
                    "rawProviderQuantity": stock_detail["available_quantity"],
                    "price": book_price,
                    "lastProviderId": provider_id,
                }
            )
            if _should_reindex_offer(stock_detail["available_quantity"], book_price, stock):
                offer_ids.add(offers_by_provider_reference[stock_detail["offers_provider_reference"]])

        else:
            if not stock_detail["available_quantity"]:
                continue
            stock = _build_stock_from_stock_detail(
                stock_detail,
                offers_by_provider_reference[stock_detail["offers_provider_reference"]],
                book_price,
                provider_id,
            )
            if not _validate_stock_or_offer(stock):
                continue

            new_stocks.append(stock)
            offer_ids.add(stock.offerId)

    return update_stock_mapping, new_stocks, offer_ids


def _build_stock_from_stock_detail(
    stock_detail: dict, offers_id: int, price: float, provider_id: Optional[int]
) -> Stock:
    return Stock(
        quantity=stock_detail["available_quantity"],
        rawProviderQuantity=stock_detail["available_quantity"],
        bookingLimitDatetime=None,
        offerId=offers_id,
        price=price,
        dateModified=datetime.now(),
        idAtProviders=stock_detail["stocks_provider_reference"],
        lastProviderId=provider_id,
    )


def _validate_stock_or_offer(model: Union[Offer, Stock]) -> bool:
    model_api_errors = validate(model)
    if model_api_errors.errors.keys():
        logger.exception(
            "[SYNC] errors while trying to add stock or offer with ref %s: %s",
            model.idAtProviders,
            model_api_errors.errors,
        )
        return False

    return True


def _build_new_offer(
    venue: Venue, product: Product, id_at_providers: str, id_at_provider: str, provider_id: Optional[int]
) -> Offer:
    return Offer(
        bookingEmail=venue.bookingEmail,
        description=product.description,
        extraData=product.extraData,
        idAtProviders=id_at_providers,
        idAtProvider=id_at_provider,
        lastProviderId=provider_id,
        name=product.name,
        productId=product.id,
        venueId=venue.id,
        type=product.type,
        subcategoryId=product.subcategoryId,
        withdrawalDetails=venue.withdrawalDetails,
    )


def _should_reindex_offer(new_quantity: int, new_price: float, existing_stock: dict) -> bool:
    if existing_stock["price"] != new_price:
        return True

    is_existing_stock_empty = existing_stock["quantity"] <= existing_stock["booking_quantity"]
    is_new_quantity_stock_empty = new_quantity == 0

    return is_existing_stock_empty != is_new_quantity_stock_empty
