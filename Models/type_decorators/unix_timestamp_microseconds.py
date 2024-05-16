from sqlalchemy.types import TypeDecorator, BigInteger
from datetime import datetime


class UnixTimestampMicroseconds(TypeDecorator):
    impl = BigInteger

    def process_bind_param(self, value, dialect):
        """Convert a datetime object to a Unix timestamp with microsecond accuracy."""
        if value is not None:
            microseconds = value.microsecond  # Extract microseconds
            return int((value.timestamp() * 1e6) + microseconds)  # Convert seconds to microseconds and add microseconds
        return None

    def process_result_value(self, value, dialect):
        """Convert a Unix timestamp with microsecond accuracy to a datetime object."""
        if value is not None:
            seconds = int(value / 1e6)
            microseconds = int(value % 1e6)
            return datetime.fromtimestamp(seconds).replace(microsecond=microseconds)
        return None
