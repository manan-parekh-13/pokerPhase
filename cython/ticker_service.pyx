from datetime import datetime
from typing import Dict, List

# Import custom functions
from equalizer.service.ticker_service import get_equivalent_tick_from_token, get_instrument_from_token
from mysql_config import add
from kiteconnect.global_stuff import add_buy_and_sell_task_to_queue
from kiteconnect.utils import get_product_type_from_ws_id
from Models.raw_ticker_data import init_raw_ticker_data
from arbitrage_service import check_arbitrage

def check_tickers_for_arbitrage(
    ticks: Dict[int, Dict[str, Any]],
    tickers_to_be_saved: List[Dict[str, Any]],
    web_socket: Any,
    kite_client: Any
) -> None:
    cdef int instrument_token, max_buy_quantity
    cdef dict latest_tick_for_instrument, latest_tick_for_equivalent
    cdef float ltp, available_margin, reqd_margin
    cdef long opportunity_check_started_at
    cdef object instrument, opportunity

    for instrument_token, latest_tick_for_instrument in ticks.items():
        opportunity_check_started_at = datetime.now()

        latest_tick_for_equivalent = get_equivalent_tick_from_token(web_socket, instrument_token)

        if not latest_tick_for_equivalent:
            continue

        ltp = latest_tick_for_instrument['depth']['sell'][0]['price']

        if ltp == 0.0:
            continue

        instrument = get_instrument_from_token(web_socket, instrument_token)

        available_margin = kite_client.get_available_margin()
        max_buy_quantity = int(available_margin / ltp)

        if max_buy_quantity == 0:
            continue

        opportunity = check_arbitrage(
            latest_tick_for_equivalent,
            latest_tick_for_instrument,
            instrument.threshold_spread_coef,
            instrument.min_profit_percent,
            instrument.product_type,
            max_buy_quantity,
            web_socket.ws_id
        )

        if not opportunity:
            continue

        opportunity.opportunity_check_started_at = opportunity_check_started_at
        instrument.leverage = instrument.leverage if instrument.leverage else 1

        if not web_socket.try_ordering:
            add(opportunity)
            continue

        reqd_margin = (opportunity.buy_price + opportunity.sell_price) * opportunity.quantity / instrument.leverage

        add_buy_and_sell_task_to_queue({
            "opportunity": opportunity,
            "product_type": get_product_type_from_ws_id(opportunity.ws_id),
            "reqd_margin": reqd_margin,
            "leverage": instrument.leverage
        })

        tickers_to_be_saved.append(init_raw_ticker_data(latest_tick_for_instrument, web_socket.ws_id))
        tickers_to_be_saved.append(init_raw_ticker_data(latest_tick_for_equivalent, web_socket.ws_id))


