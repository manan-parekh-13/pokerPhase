from sqlalchemy import Column, String, Integer, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from mysql_config import engine

Base = declarative_base()


def init_arbitrage_opportunities(buy_source, sell_source, buy_price,
                                 sell_price, quantity, buy_threshold,
                                 threshold_percentage, buy_source_ticker_time,
                                 sell_source_ticker_time, profit_percent,
                                 buy_value, created_at):
    # Create a new row for the ArbitrageOpportunity table
    return ArbitrageOpportunity(
        buy_source=buy_source,
        sell_source=sell_source,
        buy_price=buy_price,
        sell_price=sell_price,
        quantity=quantity,
        buy_threshold=buy_threshold,
        threshold_percentage=threshold_percentage,
        buy_source_ticker_time=buy_source_ticker_time,
        sell_source_ticker_time=sell_source_ticker_time,
        buy_value=buy_value,
        profit_percent=profit_percent,
        created_at=created_at
    )


class ArbitrageOpportunity(Base):
    __tablename__ = 'arbitrage_opportunities'

    id = Column(Integer, primary_key=True)
    buy_source = Column(String(255))
    sell_source = Column(String(255))
    buy_price = Column(Float)
    sell_price = Column(Float)
    quantity = Column(Integer)
    profit_percent = Column(Float)
    buy_value = Column(Float)
    buy_source_ticker_time = Column(DateTime, nullable=False)
    sell_source_ticker_time = Column(DateTime, nullable=False)
    buy_threshold = Column(Float)
    threshold_percentage = Column(Float)
    created_at = Column(DateTime, nullable=False)


Base.metadata.create_all(engine, checkfirst=True)
