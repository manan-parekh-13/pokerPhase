from sqlalchemy import Column, DECIMAL, Integer, String, Index
from sqlalchemy.ext.declarative import declarative_base
from mysql_config import engine, session
from sqlalchemy.sql import update
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
        ws_id=ws_id,
        buy_order_id=None,
        sell_order_id=None,
        buy_status=ArbitrageOpportunity.GENERATED,
        sell_status=ArbitrageOpportunity.GENERATED
    )


class ArbitrageOpportunity(Base):
    __tablename__ = 'arbitrage_opportunities'

    # Opportunity status throughout its lifecycle.
    GENERATED = "GENERATED"
    FAILED = "FAILED"
    TRIED = "TRIED"
    # Order status (subset of opportunity status lifecycle)
    REJECTED = "REJECTED" # STATUS_REJECTED
    CANCELLED = "CANCELLED" # STATUS_CANCELLED
    COMPLETE = "COMPLETE" # STATUS_COMPLETE

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
    buy_order_id = Column(Integer)
    sell_order_id = Column(Integer)
    buy_status = Column(String(20))
    sell_status = Column(String(20))

    __table_args__ = (
        Index('index_buy_order_id', 'buy_order_id'),
        Index('index_sell_order_id', 'sell_order_id'),
    )

    @classmethod
    def update_buy_status_by_buy_order_id(cls, buy_order_id, new_status):
        update_stmt = update(cls).where(cls.buy_order_id == buy_order_id).values(buy_status=new_status)
        session.execute(update_stmt)

    @classmethod
    def update_sell_status_by_sell_order_id(cls, sell_order_id, new_status):
        update_stmt = update(cls).where(cls.sell_order_id == sell_order_id).values(sell_status=new_status)
        session.execute(update_stmt)


Base.metadata.create_all(engine, checkfirst=True)
