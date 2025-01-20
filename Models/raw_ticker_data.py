from sqlalchemy import Column, Integer, BigInteger, String
from sqlalchemy.ext.declarative import declarative_base

from kiteconnect.utils import convert_depth_to_string
from mysql_config import engine

Base = declarative_base()


def init_raw_ticker_data(ticker, ws_id):
    return RawTickerData(
        instrument_token=ticker['instrument_token'],
        ticker_received_time=ticker['ticker_received_time'],
        ws_id=ws_id,
        buy_depth=convert_depth_to_string(ticker['depth']['buy']),
        sell_depth=convert_depth_to_string(ticker['depth']['sell'])
    )


class RawTickerData(Base):
    __tablename__ = 'raw_ticker_data'

    id = Column(Integer, primary_key=True)
    instrument_token = Column(Integer)
    ticker_received_time = Column(BigInteger)
    ws_id = Column(String(15))
    buy_depth = Column(String(100), nullable=True)
    sell_depth = Column(String(100), nullable=True)


Base.metadata.create_all(engine, checkfirst=True)
