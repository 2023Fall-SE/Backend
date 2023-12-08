from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import Config
from google.cloud.sql.connector import Connector, IPTypes
import sqlalchemy
import pymysql

# initialize Connector object
# if Config.DB == "mysql":
#     connector = Connector(ip_type=IPTypes.PUBLIC, enable_iam_auth=True,)
#     def getconn() -> pymysql.connections.Connection:
#         conn: pymysql.connections.Connection = connector.connect(
#             f"{Config.PROJECT_INSTANCE}",  # your Cloud SQL instance connection name
#             "pymysql",
#             user="root",
#             password=f"{Config.DB_PASSWORD}",
#             db=f"{Config.DB_NAME}"
#         )
#         return conn
#
#     # create connection pool
#     pool = sqlalchemy.create_engine(
#         "mysql+pymysql://",
#         creator=getconn,
#     )

engine = create_engine(Config.SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) 
Base = declarative_base()
