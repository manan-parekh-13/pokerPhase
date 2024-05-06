from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from mysql_config import engine

Base = declarative_base()


class RawTickerData(Base):
    __tablename__ = 'raw_ticker_data'

    id = Column(Integer, primary_key=True)
    exchange_timestamp = Column(DateTime)
    instrument_token = Column(Integer)
    tradable = Column(Boolean)
    mode = Column(String(255))
    last_price = Column(Float)
    last_traded_quantity = Column(Integer)
    average_traded_price = Column(Float)
    volume_traded = Column(Integer)
    total_buy_quantity = Column(Integer)
    total_sell_quantity = Column(Integer)
    ohlc = Column(JSON)
    change = Column(Float)
    last_trade_time = Column(DateTime)
    ticker_received_time = Column(DateTime)
    oi = Column(Integer)
    oi_day_high = Column(Integer)
    oi_day_low = Column(Integer)
    depth = Column(JSON)


Base.metadata.create_all(engine, checkfirst=True)
