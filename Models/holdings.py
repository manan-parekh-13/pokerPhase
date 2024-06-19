from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from mysql_config import engine, get_thread_session

Base = declarative_base()


class Holdings(Base):
    __tablename__ = 'holdings'

    id = Column(Integer, primary_key=True, autoincrement=True)
    authorisation = Column(String(255))
    authorised_date = Column(DateTime)
    authorised_quantity = Column(Integer)
    average_price = Column(Float)
    close_price = Column(Float)
    collateral_quantity = Column(Integer)
    collateral_type = Column(String(20))
    day_change = Column(Float)
    day_change_percentage = Column(Float)
    discrepancy = Column(Boolean)
    exchange = Column(String(20))
    instrument_token = Column(Integer)
    isin = Column(String(20))
    last_price = Column(Float)
    opening_quantity = Column(Integer)
    pnl = Column(Float)
    price = Column(Float)
    product = Column(String(20))
    quantity = Column(Integer)
    realised_quantity = Column(Integer)
    short_quantity = Column(Integer)
    t1_quantity = Column(Integer)
    tradingsymbol = Column(String(20))
    used_quantity = Column(Integer)
    arbitrage_quantity = Column(Integer)

    @classmethod
    def get_holdings_available_for_arbitrage(cls):
        session = get_thread_session()
        return session.query(cls).filter(cls.arbitrage_quantity.isnot(None)).all()


Base.metadata.create_all(engine, checkfirst=True)
