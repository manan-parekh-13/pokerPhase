from sqlalchemy import Column, DateTime, Integer, DECIMAL, String, Text, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from mysql_config import engine, get_thread_session

Base = declarative_base()


def init_order_info(order):
    fields_to_remove = []
    for field in fields_to_remove:
        if field in order:
            del order[field]

    return OrderInfo(**order)


class OrderInfo(Base):
    __tablename__ = 'order_info'

    id = Column(Integer, primary_key=True)
    account_id = Column(String(20), nullable=False)
    placed_by = Column(String(20), nullable=False)
    order_id = Column(String(20), unique=True, index=True)
    exchange_order_id = Column(String(20))
    parent_order_id = Column(String(20))
    status = Column(String(20), nullable=False)
    status_message = Column(Text)
    status_message_raw = Column(Text)
    order_timestamp = Column(DateTime, nullable=False)
    exchange_update_timestamp = Column(DateTime)
    exchange_timestamp = Column(DateTime, nullable=True)
    variety = Column(String(20))
    modified = Column(Boolean)
    exchange = Column(String(10), nullable=False)
    tradingsymbol = Column(String(30), nullable=False)
    instrument_token = Column(Integer, nullable=False)
    order_type = Column(String(10), nullable=False)
    transaction_type = Column(String(10), nullable=False)
    validity = Column(String(10), nullable=False)
    validity_ttl = Column(Integer, nullable=False)
    product = Column(String(10), nullable=False)
    quantity = Column(Integer, nullable=False)
    disclosed_quantity = Column(Integer, nullable=False)
    price = Column(DECIMAL(8, 2), nullable=False)
    trigger_price = Column(DECIMAL(8, 2))
    average_price = Column(DECIMAL(8, 2), nullable=False)
    filled_quantity = Column(Integer, nullable=False)
    pending_quantity = Column(Integer, nullable=False)
    cancelled_quantity = Column(Integer, nullable=False)
    market_protection = Column(Integer)
    meta = Column(JSON)
    tag = Column(String(50))
    guid = Column(String(50))

    @classmethod
    def get_order_by_id(cls, order_id: str):
        """
        Fetch a row from the Order table by order_id.

        :param order_id: The order ID to filter
        :return: An Order object or None if not found
        """
        session = get_thread_session()
        return session.query(cls).filter(cls.order_id == order_id).first()


Base.metadata.create_all(engine, checkfirst=True)
