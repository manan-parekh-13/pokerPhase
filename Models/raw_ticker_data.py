from sqlalchemy import Column, Integer, DECIMAL, Boolean, JSON, String
from sqlalchemy.ext.declarative import declarative_base
from mysql_config import engine
from Models.type_decorators.unix_timestamp_seconds import UnixTimestampSeconds
from Models.type_decorators.unix_timestamp_microseconds import UnixTimestampMicroseconds

Base = declarative_base()


def init_raw_ticker_data(ticker, ws_id):
    return RawTickerData(
        exchange_timestamp=ticker['exchange_timestamp'],
        instrument_token=ticker['instrument_token'],
        tradable=ticker['tradable'],
        last_price=ticker['last_price'],
        last_traded_quantity=ticker['last_traded_quantity'],
        last_trade_time=ticker['last_trade_time'],
        ticker_received_time=ticker['ticker_received_time'],
        depth=ticker['depth'],
        ws_id=ws_id
    )


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
    ws_id = Column(String(15))


Base.metadata.create_all(engine, checkfirst=True)
