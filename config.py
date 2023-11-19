import os
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()
class Config(object):
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DB_PATH = os.path.abspath(os.getcwd()) + "/database/carpool_test.db"
    SQLALCHEMY_DATABASE_URL = "sqlite:///" + DB_PATH
    # SQLALCHEMY_DATABASE_URL = 'mysql://root:pwd@localhost:3306/name'
    SECRET_KEY = "key_testing"

    JWT_SECRET_KEY = "jwt_key_testing"
    JWT_ALGORITHM = "HS256"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(seconds=60)

    ENVIRONMENT = os.getenv("ENVIRONMENT")
    RELEASE_VERSION = "0.0.1"
