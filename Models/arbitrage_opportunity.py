from sqlalchemy import Column, DECIMAL, Integer, Index
from sqlalchemy.ext.declarative import declarative_base
from mysql_config import engine
from Models.type_decorators.unix_timestamp_microseconds import UnixTimestampMicroseconds
from kiteconnect.login import set_timezone_in_datetime
from datetime import datetime

Base = declarative_base()


def init_arbitrage_opportunities_from_strat_res_and_tickers(buy_ticker, sell_ticker, strat_result, ws_id):
    return ArbitrageOpportunity(
        buy_source=buy_ticker['instrument_token'],
        sell_source=sell_ticker['instrument_token'],
        buy_price=strat_result['buy_price'],
        sell_price=strat_result['sell_price'],
        quantity=strat_result['quantity'],
        buy_source_ticker_time=buy_ticker['ticker_received_time'],
        sell_source_ticker_time=sell_ticker['ticker_received_time'],
        created_at=set_timezone_in_datetime(datetime.now()),
        ws_id=ws_id,
        buy_order_id=None,
        sell_order_id=None,
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
    buy_order_id = Column(Integer)
    sell_order_id = Column(Integer)

    __table_args__ = (
        Index('index_buy_order_id', 'buy_order_id'),
        Index('index_sell_order_id', 'sell_order_id'),
    )


Base.metadata.create_all(engine, checkfirst=True)
