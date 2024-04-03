from sqlalchemy import Column, String, Integer, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from mysql_config import engine

Base = declarative_base()


class DepthData(Base):
    __tablename__ = 'depth_data'

    id = Column(Integer, primary_key=True)
    exchange_timestamp = Column(DateTime, nullable=False)
    instrument_token = Column(Integer, nullable=False)
    type = Column(String(255), nullable=False)  # 'buy' or 'sell'
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    orders = Column(Integer, nullable=False)


Base.metadata.create_all(engine, checkfirst=True)
