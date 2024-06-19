import os
import logging
import threading
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
Session = sessionmaker(bind=engine)
default_session = Session()

thread_local = threading.local()


def init_thread_session():
    thread_local.session = Session()


def get_thread_session():
    if not hasattr(thread_local, 'session'):
        init_thread_session()
    return thread_local.session


# Function to close the session
def close_session():
    session = get_thread_session()
    session.close()


def add(entry):
    session = get_thread_session()
    try:
        session.add(entry)
        session.commit()
        logging.debug("Added entry with session {}".format(id(session)))
    except Exception as e:
        session.rollback()
        logging.error(f"Rollback due to exception: {e}")


def add_all(entries):
    session = get_thread_session()
    try:
        session.add_all(entries)
        session.commit()
        logging.debug("Added entries with session {}".format(id(session)))
    except Exception as e:
        session.rollback()
        logging.error(f"Rollback due to exception: {e}")
