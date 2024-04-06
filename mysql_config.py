from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from kiteconnect.utils import get_sensitive_parameter

mysql_user_name = get_sensitive_parameter("MYSQL_USER_NAME")
mysql_password = get_sensitive_parameter("MYSQL_PASSWORD")
mysql_host = get_sensitive_parameter("MYSQL_HOST")
mysql_port = 3307  # Update with the new port number

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