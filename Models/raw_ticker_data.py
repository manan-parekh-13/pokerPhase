from sqlalchemy import Column, Integer, DECIMAL, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from mysql_config import engine
from Models.type_decorators.unix_timestamp_seconds import UnixTimestampSeconds
from Models.type_decorators.unix_timestamp_microseconds import UnixTimestampMicroseconds

Base = declarative_base()


class RawTickerData(Base):
    __tablename__ = 'raw_ticker_data'

    id = Column(Integer, primary_key=True)
    exchange_timestamp = Column(UnixTimestampSeconds)
    instrument_token = Column(Integer)
    tradable = Column(Boolean)
    last_price = Column(DECIMAL(8, 2))
    last_traded_quantity = Column(Integer)
    last_trade_time = Column(UnixTimestampSeconds)
    ticker_received_time = Column(UnixTimestampMicroseconds)
    depth = Column(JSON)


Base.metadata.create_all(engine, checkfirst=True)
