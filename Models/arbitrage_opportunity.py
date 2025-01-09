from sqlalchemy import Column, DECIMAL, Integer, Index, Boolean, String, desc
from sqlalchemy.ext.declarative import declarative_base
from mysql_config import engine, get_thread_session
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
        created_at=datetime.now(),
        ws_id=ws_id,
        buy_order_id=None,
        sell_order_id=None,
        is_stale=False,
        order_on_hold=False,
        opportunity_check_started_at=None,
        opp_added_to_queue_at=None,
        opp_received_in_queue_at=None,
        opp_buy_task_created_at=None,
        opp_buy_task_received_at=None,
        buy_ordered_at=None,
        opp_sell_task_created_at=None,
        opp_sell_task_received_at=None,
        sell_ordered_at=None
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
    ws_id = Column(String(15))
    buy_order_id = Column(Integer)
    sell_order_id = Column(Integer)
    is_stale = Column(Boolean)
    order_on_hold = Column(Boolean)
    opportunity_check_started_at = Column(UnixTimestampMicroseconds)
    opp_added_to_queue_at = Column(UnixTimestampMicroseconds)
    opp_received_in_queue_at = Column(UnixTimestampMicroseconds)
    opp_buy_task_created_at = Column(UnixTimestampMicroseconds)
    opp_buy_task_received_at = Column(UnixTimestampMicroseconds)
    buy_ordered_at = Column(UnixTimestampMicroseconds)
    opp_sell_task_created_at = Column(UnixTimestampMicroseconds)
    opp_sell_task_received_at = Column(UnixTimestampMicroseconds)
    sell_ordered_at = Column(UnixTimestampMicroseconds)

    __table_args__ = (
        Index('index_buy_order_id', 'buy_order_id'),
        Index('index_sell_order_id', 'sell_order_id'),
    )

    @classmethod
    def get_latest_arbitrage_opportunity_by_id(cls):
        session = get_thread_session()
        return session.query(cls).order_by(desc(cls.id)).first()


Base.metadata.create_all(engine, checkfirst=True)
