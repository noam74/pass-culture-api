from flask import Flask
from flask_script import Manager
import redis

from pcapi import settings
from pcapi.models.db import db
from pcapi.scripts.install import install_scripts


app = Flask(__name__, template_folder="../templates")
app.config["SQLALCHEMY_DATABASE_URI"] = settings.DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)


def create_app(env=None):
    app.env = env
    return app


app.manager = Manager(create_app)

with app.app_context():
    install_scripts()

    app.redis_client = redis.from_url(url=settings.REDIS_URL, decode_responses=True)


if __name__ == "__main__":
    app.manager.run()
