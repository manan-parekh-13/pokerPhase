from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import validates
from mysql_config import engine
from datetime import datetime

Base = declarative_base()


class TickerData(Base):
    __tablename__ = 'ticker_data'

    id = Column(Integer, primary_key=True)
    exchange_timestamp = Column(DateTime)
    instrument_token = Column(Integer, nullable=False)
    tradable = Column(Boolean, nullable=False)
    mode = Column(String(255), nullable=False)
    last_price = Column(Float, nullable=False)
    last_traded_quantity = Column(Integer)
    average_traded_price = Column(Float)
    volume_traded = Column(Integer)
    total_buy_quantity = Column(Integer)
    total_sell_quantity = Column(Integer)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    change = Column(Float)
    last_trade_time = Column(DateTime)
    ticker_received_time = Column(DateTime, nullable=False)
    oi = Column(Integer)
    oi_day_high = Column(Integer)
    oi_day_low = Column(Integer)

    @validates('instrument_token')
    def validate_instrument_token(self, key, instrument_token):
        assert isinstance(instrument_token, int), "Instrument token must be an integer."
        return instrument_token

    @validates('ticker_received_time')
    def validate_ticker_received_time(self, key, ticker_received_time):
        assert isinstance(ticker_received_time, datetime), "Ticker received time must be a date."
        return ticker_received_time

    @validates('last_price')
    def validate_last_price(self, key, last_price):
        assert isinstance(last_price, float), "Last price must be a float."
        return last_price

    @validates('mode')
    def validate_mode(self, key, mode):
        assert mode in ['full', 'ltp', 'quote'], "Mode must be either 'full' or 'ltp' or 'quote'."
        return mode

    @validates('tradable')
    def validate_tradable(self, key, tradable):
        assert isinstance(tradable, bool), "Tradable must be a boolean."
        return tradable

    # __table_args__ = (
    #     # Define a unique constraint on ticker_received_time and instrument_token
    #     UniqueConstraint('ticker_received_time', 'instrument_token'),
    # )


Base.metadata.create_all(engine, checkfirst=True)
