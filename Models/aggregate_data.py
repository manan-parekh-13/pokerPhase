from sqlalchemy import Column, Integer, String, Float
from Models.type_decorators.unix_timestamp_seconds import UnixTimestampSeconds
from sqlalchemy.ext.declarative import declarative_base
from mysql_config import engine
from datetime import datetime
import math

Base = declarative_base()


def init_aggregate_data_for_instrument_and_ws_id(data, instrument_token, ws_id):
    avg_time_diff = 0
    if 'n' in data and data.get('n') != 0:
        avg_time_diff = data.get('sum_of_time_diff') / data.get('n')
        std_dev_time_diff = math.sqrt((data.get('sum_of_square_of_time_diff') / data.get('n')) -
                                      avg_time_diff ** 2)
    return AggregateData(
        started_at=data.get('started_at'),
        created_at=datetime.now(),
        instrument_token=instrument_token,
        max_time_diff=data.get('max'),
        min_time_diff=data.get('min'),
        avg_tim_diff=avg_time_diff,
        std_dev_time_diff=std_dev_time_diff,
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
