from sqlalchemy.types import TypeDecorator, Integer
from datetime import datetime


class UnixTimestampSeconds(TypeDecorator):
    impl = Integer

    def process_bind_param(self, value, dialect):
        """Convert a datetime object to a Unix timestamp with second accuracy."""
        if value is not None:
            return int(value.timestamp())
        return None

    def process_result_value(self, value, dialect):
        """Convert a Unix timestamp with second accuracy to a datetime object."""
        if value is not None:
            return datetime.fromtimestamp(value)
        return None
