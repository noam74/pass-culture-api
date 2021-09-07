from pathlib import Path

from sqlalchemy.sql.functions import func

from pcapi.core.users.external.sendinblue import import_contacts_in_sendinblue
from pcapi.core.users.models import User
from pcapi.flask_app import app
from pcapi.models import db
from pcapi.scripts.batch_update_users_attributes import format_sendinblue_users


def _get_emails() -> list[str]:
    unsubscribed_mailjet_users = []
    script_execution_dir = Path().resolve()

    file_to_open = script_execution_dir / "unsubscribed_mailjet_users.txt"

    # Expecting unsubscribed_mailjet_users.txt to be a text file containing one email per line
    with open(file_to_open, "r") as file:
        unsubscribed_mailjet_users = file.read().splitlines()
    return unsubscribed_mailjet_users


def synchronize_subscription_status_with_mailjet() -> None:
    print("\nPlease execute this script in the same directory as unsubscribed_mailjet_users.txt")
    print("To check current path:\nfrom pathlib import Path\nPath().resolve()\n")
    unsubscribed_mailjet_users = _get_emails()
    with app.app_context():
        users_to_update = User.query.filter(User.email.in_(unsubscribed_mailjet_users))
        updated_users = users_to_update.update(
            values={
                "notificationSubscriptions": func.jsonb_set(
                    User.notificationSubscriptions, '{"marketing_email"}', "false"
                )
            },
            synchronize_session=False,
        )
        db.session.commit()

    print("Updated %s users out of %s" % (updated_users, len(unsubscribed_mailjet_users)))
    if updated_users < len(unsubscribed_mailjet_users):
        not_found_emails = [
            email
            for email in unsubscribed_mailjet_users
            if db.session.query(User.id).filter(User.email == email).first() is None
        ]
        print("Emails not found in db: %s" % not_found_emails)

    sendinblue_users_data = format_sendinblue_users(users_to_update.all())
    import_contacts_in_sendinblue(sendinblue_users_data)
