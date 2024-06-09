from sqlalchemy import Column, Integer, String, Float
from Models.type_decorators.unix_timestamp_seconds import UnixTimestampSeconds
from sqlalchemy.ext.declarative import declarative_base
from mysql_config import engine
from datetime import datetime
import math

Base = declarative_base()


def init_aggregate_data_for_instrument_and_ws_id(data, instrument_token, ws_id):
    return AggregateData(
        started_at=data['started_at'],
        created_at=datetime.now(),
        instrument_token=instrument_token,
        max_time_diff=data['max'],
        min_time_diff=data['min'],
        avg_tim_diff=data['sum_of_time_diff'] / data['n'],
        std_dev_time_diff=math.sqrt((data['sum_of_square_of_time_diff'] / data['n']) -
                                    (data['sum_of_time_diff'] / data['n']) ** 2),
        ws_id=ws_id
    )


class AggregateData(Base):
    __tablename__ = 'aggregate_data'

    id = Column(Integer, primary_key=True, autoincrement=True)
    started_at = Column(UnixTimestampSeconds)
    created_at = Column(UnixTimestampSeconds)
    instrument_token = Column(Integer)
    max_time_diff = Column(Float)
    min_time_diff = Column(Float)
    avg_tim_diff = Column(Float)
    std_dev_time_diff = Column(Float)
    ws_id = Column(String(15))


Base.metadata.create_all(engine, checkfirst=True)