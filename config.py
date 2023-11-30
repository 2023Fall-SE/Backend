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

    LICENSE_UPLOAD_PATH = os.path.abspath(os.getcwd()) + "/license/"

    ENVIRONMENT = os.getenv("ENVIRONMENT")
    RELEASE_VERSION = "0.0.1"
    
    LINE_PAY_CHANNELID="2001918325"
    LINE_PAY_SECRET="3890889e7730561c29fb4f9956f0910b"
    LINE_PAY_VERSION="v3"
    LINE_PAY_SITE="https://sandbox-api-pay.line.me"
