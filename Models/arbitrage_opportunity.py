from sqlalchemy import Column, DECIMAL, Integer
from sqlalchemy.ext.declarative import declarative_base
from mysql_config import engine
from Models.type_decorators.unix_timestamp_seconds import UnixTimestampSeconds
from Models.type_decorators.unix_timestamp_microseconds import UnixTimestampMicroseconds

Base = declarative_base()


def init_arbitrage_opportunities(buy_source, sell_source, buy_price,
                                 sell_price, quantity, buy_source_ticker_time,
                                 sell_source_ticker_time, created_at):
    # Create a new row for the ArbitrageOpportunity table
    return ArbitrageOpportunity(
        buy_source=buy_source,
        sell_source=sell_source,
        buy_price=buy_price,
        sell_price=sell_price,
        quantity=quantity,
        buy_source_ticker_time=buy_source_ticker_time,
        sell_source_ticker_time=sell_source_ticker_time,
        created_at=created_at
    )


class ArbitrageOpportunity(Base):
    __tablename__ = 'arbitrage_opportunities'

    id = Column(Integer, primary_key=True)
    buy_source = Column(Integer)
    sell_source = Column(Integer)
    buy_price = Column(DECIMAL(8, 2))
    sell_price = Column(DECIMAL(8, 2))
    quantity = Column(Integer)
    buy_source_ticker_time = Column(UnixTimestampSeconds, nullable=False)
    sell_source_ticker_time = Column(UnixTimestampSeconds, nullable=False)
    created_at = Column(UnixTimestampMicroseconds, nullable=False)


Base.metadata.create_all(engine, checkfirst=True)
