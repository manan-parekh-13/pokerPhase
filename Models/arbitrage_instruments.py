from sqlalchemy import Column, String, Integer, Float, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from mysql_config import engine, get_thread_session

Base = declarative_base()


class ArbitrageInstruments(Base):
    __tablename__ = 'arbitrage_instruments'

    id = Column(Integer, primary_key=True, autoincrement=True)
    trading_symbol = Column(String(255), nullable=False)
    name1 = Column(String(255), nullable=False)
    name2 = Column(String(255), nullable=False)
    exchange1 = Column(String(10), nullable=False)
    exchange2 = Column(String(10), nullable=False)
    segment1 = Column(String(10), nullable=False)
    segment2 = Column(String(10), nullable=False)
    exchange_token1 = Column(Integer, nullable=False)
    exchange_token2 = Column(Integer, nullable=False)
    instrument_token1 = Column(Integer, nullable=False)
    instrument_token2 = Column(Integer, nullable=False)
    min_profit_percent = Column(Float)
    product_type = Column(JSON)
    try_ordering = Column(Boolean)
    leverage = Column(Integer)

    @classmethod
    def get_arbitrage_instruments(cls):
        session = get_thread_session()
        return session.query(cls).all()


Base.metadata.create_all(engine, checkfirst=True)