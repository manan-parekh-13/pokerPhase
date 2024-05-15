from sqlalchemy import Column, String, Integer, Boolean, Float
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
    check_for_opportunity = Column(Boolean, nullable=False)
    threshold_percentage = Column(Float)
    buy_threshold = Column(Float)
    max_buy_value = Column(Float)

    @classmethod
    def get_instruments_by_check_for_opportunity(cls, check_for_opportunity):
        return session.query(cls).filter(cls.check_for_opportunity == check_for_opportunity).all()


Base.metadata.create_all(engine, checkfirst=True)