from sqlalchemy import Column, String, Integer, Float
from sqlalchemy.ext.declarative import declarative_base
from equalizer.mysql_config import engine

Base = declarative_base()


def convert(input_instance):
    if not input_instance:
        return None
    input_instance["name"] = input_instance["name"].strip()
    return Instrument(**input_instance)


def convert_all(input_instances):
    if not input_instances:
        return []
    return map(lambda x: convert(x), input_instances)


class Instrument(Base):
    __tablename__ = 'instruments'

    id = Column(Integer, primary_key=True)
    exchange = Column(String(255))
    exchange_token = Column(String(255))
    tradingsymbol = Column(String(255))
    expiry = Column(String(255))
    instrument_token = Column(Integer)
    instrument_type = Column(String(255))
    last_price = Column(Float)
    lot_size = Column(Integer)
    name = Column(String(255))
    segment = Column(String(255))
    strike = Column(Float)
    tick_size = Column(Float)


# Create the table if it does not exist
Base.metadata.create_all(engine, checkfirst=True)
