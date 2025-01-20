from sqlalchemy import Column, DECIMAL, Integer, Boolean, String, desc, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from kiteconnect.utils import convert_date_time_to_us
from mysql_config import engine, get_thread_session
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
        created_at=convert_date_time_to_us(datetime.now()),
        ws_id=ws_id,
        buy_order_id=None,
        sell_order_id=None,
        is_stale=False,
        order_on_hold=False,
        low_margin_hold=False,
        opportunity_check_started_at=None,
        opp_buy_task_received_at=None,
        buy_ordered_at=None,
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
    buy_source_ticker_time = Column(BigInteger)
    sell_source_ticker_time = Column(BigInteger)
    created_at = Column(BigInteger)
    ws_id = Column(String(15))
    buy_order_id = Column(Integer)
    sell_order_id = Column(Integer)
    is_stale = Column(Boolean)
    order_on_hold = Column(Boolean)
    low_margin_hold = Column(Boolean)
    opportunity_check_started_at = Column(BigInteger)
    opp_buy_task_received_at = Column(BigInteger)
    buy_ordered_at = Column(BigInteger)
    opp_sell_task_received_at = Column(BigInteger)
    sell_ordered_at = Column(BigInteger)

    @classmethod
    def get_latest_arbitrage_opportunity_by_id(cls):
        session = get_thread_session()
        return session.query(cls).order_by(desc(cls.id)).first()


Base.metadata.create_all(engine, checkfirst=True)
