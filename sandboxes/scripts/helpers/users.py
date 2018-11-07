from models import User
from models.pc_object import PcObject
from sandboxes.scripts.utils.storage_utils import store_public_object_from_sandbox_assets
from utils.human_ids import dehumanize
from utils.logger import logger

def create_or_find_user(user_mock):
    logger.info('look user ' + user_mock['email'] + " " + user_mock.get('id'))

    if 'id' in user_mock:
        user = User.query.get(dehumanize(user_mock['id']))
    else:
        user = User.query.filter_by(email=user_mock['email']).first()

    if user is None:
        user = User(from_dict=user_mock)
        if 'id' in user_mock:
            user.id = dehumanize(user_mock['id'])
        PcObject.check_and_save(user)
        logger.info("created user"  + str(user) + " " + user_mock['email'])
        if 'thumbName' in user_mock:
            store_public_object_from_sandbox_assets("thumbs", user, user_mock['thumbName'])
    else:
        logger.info('--aleady here-- user' + str(user))

    return user
