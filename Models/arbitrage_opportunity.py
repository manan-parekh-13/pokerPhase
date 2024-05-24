from sqlalchemy import Column, DECIMAL, Integer
from sqlalchemy.ext.declarative import declarative_base
from mysql_config import engine
from Models.type_decorators.unix_timestamp_microseconds import UnixTimestampMicroseconds

Base = declarative_base()


def init_arbitrage_opportunities(buy_source, sell_source, buy_price,
                                 sell_price, quantity, buy_source_ticker_time,
                                 sell_source_ticker_time, created_at, ws_id):
    # Create a new row for the ArbitrageOpportunity table
    return ArbitrageOpportunity(
        buy_source=buy_source,
        sell_source=sell_source,
        buy_price=buy_price,
        sell_price=sell_price,
        quantity=quantity,
        buy_source_ticker_time=buy_source_ticker_time,
        sell_source_ticker_time=sell_source_ticker_time,
        created_at=created_at,
        ws_id=ws_id
    )


class ArbitrageOpportunity(Base):
    __tablename__ = 'arbitrage_opportunities'

    id = Column(Integer, primary_key=True)
    buy_source = Column(Integer)
    sell_source = Column(Integer)
    buy_price = Column(DECIMAL(8, 2))
    sell_price = Column(DECIMAL(8, 2))
    quantity = Column(Integer)
    buy_source_ticker_time = Column(UnixTimestampMicroseconds)
    sell_source_ticker_time = Column(UnixTimestampMicroseconds)
    created_at = Column(UnixTimestampMicroseconds)
    ws_id = Column(Integer)


Base.metadata.create_all(engine, checkfirst=True)
