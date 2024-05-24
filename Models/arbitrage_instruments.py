from sqlalchemy import Column, String, Integer, Float
from sqlalchemy.ext.declarative import declarative_base
from mysql_config import engine, session

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
    threshold_percentage = Column(Float)
    buy_threshold = Column(Float)
    max_buy_value = Column(Float)
    ws_id = Column(Integer)

    @classmethod
    def get_instruments_with_non_null_ws_id(cls):
        return session.query(cls).filter(cls.ws_id.isnot(None)).all()


Base.metadata.create_all(engine, checkfirst=True)