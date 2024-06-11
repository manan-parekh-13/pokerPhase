import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from environment.loader import load_environment
from kiteconnect.utils import get_env_variable

# Load the environment configuration
environment = os.getenv('FLASK_ENV')
load_environment(environment)

mysql_user_name = get_env_variable("MYSQL_USER_NAME")
mysql_password = get_env_variable("MYSQL_PASSWORD")
mysql_host = get_env_variable("MYSQL_HOST")
mysql_port = get_env_variable("MYSQL_PORT")

# Database connection URL
DATABASE_URL = f"mysql+mysqlconnector://{mysql_user_name}:{mysql_password}@{mysql_host}:{mysql_port}/pokerPhase"

# Create the engine
engine = create_engine(DATABASE_URL)

# Create a session
Session = sessionmaker(bind=engine)
session = Session()


# Function to close the session
def close_session():
    session.close()


def add(entry):
    session.add(entry)
    session.commit()
    return entry


def add_all(entries):
    session.add_all(entries)
    session.commit()


def add_all_and_flush(entries):
    # try:
        session.add_all(entries)
        session.flush()
        session.commit()
    # except Exception as e:
    #     session.rollback()
    #     logging.error("Error while saving and flushing entries of type {}"
    #                   .format("No entries" if not entries else type(entries[0])), e)