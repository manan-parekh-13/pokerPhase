from Models.raw_ticker_data import init_raw_ticker_data
from kiteconnect.global_stuff import get_latest_tick_by_instrument_token_from_global_cache, \
    add_buy_and_sell_task_to_queue
from datetime import datetime
from mysql_config import add
from kiteconnect.utils import get_product_type_from_ws_id, convert_date_time_to_us
from equalizer.service.arbitrage_service import check_arbitrage


def is_ticker_stale(ticker):
    latest_ticker_for_instrument = get_latest_tick_by_instrument_token_from_global_cache(ticker['instrument_token'])
    return latest_ticker_for_instrument['ticker_received_time'] > ticker['ticker_received_time']


def is_opportunity_stale(opportunity):
    latest_tick_for_buy_source = get_latest_tick_by_instrument_token_from_global_cache(opportunity.buy_source)
    if latest_tick_for_buy_source['ticker_received_time'] > opportunity.buy_source_ticker_time:
        return True

    latest_tick_for_sell_source = get_latest_tick_by_instrument_token_from_global_cache(opportunity.sell_source)
    if latest_tick_for_sell_source['ticker_received_time'] > opportunity.sell_source_ticker_time:
        return True

    return False


def check_tickers_for_arbitrage(ticks, tickers_to_be_saved, web_socket, kite_client):
    for instrument_token, latest_tick_for_instrument in ticks.items():
        opportunity_check_started_at = convert_date_time_to_us(datetime.now())

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

        opportunity = check_arbitrage(latest_tick_for_equivalent, latest_tick_for_instrument,
                                      instrument.threshold_spread_coef, instrument.min_profit_percent,
                                      instrument.product_type, max_buy_quantity, web_socket.ws_id)

        if not opportunity:
            continue

        opportunity.opportunity_check_started_at = opportunity_check_started_at
        instrument.leverage = instrument.leverage if instrument.leverage else 1

        if not web_socket.try_ordering:
            add(opportunity)
            continue

        add_buy_and_sell_task_to_queue({
            "opportunity": opportunity,
            "product_type": get_product_type_from_ws_id(opportunity.ws_id),
            "reqd_margin": (opportunity.buy_price + opportunity.sell_price) * opportunity.quantity / instrument.leverage,
            "leverage": instrument.leverage
        })
        tickers_to_be_saved.append(init_raw_ticker_data(latest_tick_for_instrument, web_socket.ws_id))
        tickers_to_be_saved.append(init_raw_ticker_data(latest_tick_for_equivalent, web_socket.ws_id))


def get_instrument_from_token(ws, instrument_token):
    return ws.token_map.get(instrument_token)


def get_equivalent_tick_from_token(ws, instrument_token):
    instrument = get_instrument_from_token(ws, instrument_token)
    equivalent_token = instrument.equivalent_token
    return get_latest_tick_by_instrument_token_from_global_cache(equivalent_token)
