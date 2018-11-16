from models.pc_object import PcObject
from utils.logger import logger
from utils.test_utils import create_offerer

def create_handmade_offerers():
    logger.info('create_handmade_offerers')

    offerers_by_name = {}

    offerers_by_name['LE GRAND REX PARIS'] = create_offerer(
        address="1 BD POISSONNIERE",
        city="Paris",
        name="LE GRAND REX PARIS",
        postal_code="75002",
        siren="507633576"
    )

    offerers_by_name['THEATRE DE L ODEON'] = create_offerer(
        address="6 RUE GROLEE",
        city="Lyon",
        name="THEATRE DE L ODEON",
        postal_code="69002",
        siren="750505703"
    )

    offerers_by_name['THEATRE DU SOLEIL'] = create_offerer(
        address="LIEU DIT CARTOUCHERIE",
        city="Paris 12",
        name="THEATRE DU SOLEIL",
        postal_code="75012",
        siren="784340093"
    )

    offerers_by_name['KWATA'] = create_offerer(
        address="16 AVENUE PASTEUR",
        city="Cayenne",
        name="KWATA",
        postal_code="97335",
        siren="399244474"
    )

    PcObject.check_and_save(*offerers_by_name.values())

    logger.info('created {} offerers'.format(len(offerers_by_name)))

    return offerers_by_name
