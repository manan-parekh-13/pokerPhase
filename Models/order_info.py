from sqlalchemy import Column, DateTime, Integer, DECIMAL, String
from sqlalchemy.ext.declarative import declarative_base
from mysql_config import engine
from Models.type_decorators.unix_timestamp_microseconds import UnixTimestampMicroseconds

Base = declarative_base()


def init_order_info_from_order_update(order_update, update_received_time):
    fields_to_remove = ['app_id', 'checksum', 'placed_by', 'status_message_raw', 'market_protection', 'meta', 'tag',
                        'guid']
    for field in fields_to_remove:
        if field in order_update:
            del order_update[field]

    order_update['update_received_time'] = update_received_time

    return OrderInfo(**order_update)


class OrderInfo(Base):
    __tablename__ = 'order_info'

    id = Column(Integer, primary_key=True)
    user_id = Column(String(10))
    unfilled_quantity = Column(Integer)
    order_id = Column(Integer)
    exchange_order_id = Column(Integer)
    parent_order_id = Column(Integer)
    status = Column(String(10))
    order_timestamp = Column(DateTime)
    exchange_update_timestamp = Column(DateTime)
    exchange_timestamp = Column(DateTime)
    variety = Column(String(10))
    exchange = Column(String(10))
    tradingsymbol = Column(String(20))
    instrument_token = Column(Integer)
    order_type = Column(String(10))
    transaction_type = Column(String(10))
    validity = Column(String(10))
    product = Column(String(10))
    quantity = Column(Integer)
    disclosed_quantity = Column(Integer)
    price = Column(DECIMAL(8, 2))
    trigger_price = Column(DECIMAL(8, 2))
    average_price = Column(DECIMAL(8, 2))
    filled_quantity = Column(Integer)
    pending_quantity = Column(Integer)
    cancelled_quantity = Column(Integer)
    update_received_time = Column(UnixTimestampMicroseconds)


Base.metadata.create_all(engine, checkfirst=True)
