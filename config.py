import os
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()
class Config(object):
    BACKEND_URL="http://127.0.0.1:8080"
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DB_PATH = os.path.abspath(os.getcwd()) + "/database/carpool_test.db"
    SQLALCHEMY_DATABASE_URL = "sqlite:///" + DB_PATH
    SECRET_KEY = "key_testing"
    
    DB = "sqlite"
    DB_PASSWORD = os.getenv("MYSQL_PASSWORD")
    DB_IP = os.getenv("MYSQL_IP")
    DB_NAME = os.getenv("MYSQL_NAME")
    PROJECT_INSTANCE = os.getenv("PROJECT_INSTANCE")

    JWT_SECRET_KEY = "jwt_key_testing"
    JWT_ALGORITHM = "HS256"
    EXPIRE_SECOND = 60 * 60 *6
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(seconds=EXPIRE_SECOND)

    LICENSE_UPLOAD_PATH = os.path.abspath(os.getcwd()) + "/license/"

    ENVIRONMENT = os.getenv("ENVIRONMENT")
    RELEASE_VERSION = "0.0.1"
    
    LINE_PAY_CHANNELID="2001918325"
    LINE_PAY_SECRET="3890889e7730561c29fb4f9956f0910b"
    LINE_PAY_VERSION="v3"
    LINE_PAY_SITE="https://sandbox-api-pay.line.me"
    
    PUSHER_SECRET="89695078D7DDB222424BE8E5AB5E1ABB43799BE9145EF83E5EAED5EAC09D3256"
    PUSHER_INSTANCE_ID="f6cd0c10-192e-4b49-9851-980cc7a0ab3d"
