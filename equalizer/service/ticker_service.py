import asyncio
import logging
import os

from Models.raw_ticker_data import init_raw_ticker_data
from equalizer.service.order_service import consume_buy_or_sell_tasks
from kiteconnect.exceptions import OrderException
from kiteconnect.global_stuff import get_latest_tick_by_instrument_token_from_global_cache, \
    get_available_margin, add_margin, remove_order_task_if_avl, remove_margin_or_throw_error, add_to_avl_order_task
from datetime import datetime
from mysql_config import add
from kiteconnect.utils import get_product_type_from_ws_id, convert_date_time_to_us, log_info_and_notify
from equalizer.service.arbitrage_service import check_arbitrage


def is_ticker_stale(ticker):
    latest_ticker_for_instrument = get_latest_tick_by_instrument_token_from_global_cache(ticker['instrument_token'])
    return latest_ticker_for_instrument['ticker_received_time'] > ticker['ticker_received_time']


def check_tickers_for_arbitrage(ticks, tickers_to_be_saved, web_socket, kite_client):
    for instrument_token, latest_tick_for_instrument in ticks.items():
        opportunity_check_started_at = convert_date_time_to_us(datetime.now())

        instrument = get_instrument_from_token(web_socket, instrument_token)
        equivalent_token = instrument.equivalent_token
        latest_tick_for_equivalent = get_latest_tick_by_instrument_token_from_global_cache(equivalent_token)

        if not latest_tick_for_equivalent:
            continue

        ltp = latest_tick_for_instrument['depth']['sell'][0]['price']

        if ltp == 0.0:
            continue

        available_margin = get_available_margin()
        max_buy_quantity = int(available_margin / ltp)

        if max_buy_quantity == 0:
            continue

        opportunity = check_arbitrage(latest_tick_for_equivalent, latest_tick_for_instrument,
                                      instrument.threshold_spread_coef, instrument.min_profit_percent,
                                      instrument.product_type_int, max_buy_quantity, web_socket.ws_id)

        if not opportunity:
            continue

        opportunity.opportunity_check_started_at = opportunity_check_started_at
        instrument.leverage = instrument.leverage if instrument.leverage else 1

        if not web_socket.try_ordering:
            add(opportunity)
            continue

        equivalent_instrument = get_instrument_from_token(web_socket, equivalent_token)

        add_buy_and_sell_task_to_queue({
            "opportunity": opportunity,
            "product_type": get_product_type_from_ws_id(opportunity.ws_id),
            "reqd_margin": (opportunity.buy_price + opportunity.sell_price) * opportunity.quantity / instrument.leverage,
            "leverage": instrument.leverage,
            "trading_symbol": instrument.trading_symbol,
            "buy_exchange": instrument.exchange if instrument.instrument_token == opportunity.buy_source else equivalent_instrument.exchange,
            "sell_exchange": instrument.exchange if instrument.instrument_token == opportunity.sell_source else equivalent_instrument.exchange
        })
        tickers_to_be_saved.append(init_raw_ticker_data(latest_tick_for_instrument, web_socket.ws_id))
        tickers_to_be_saved.append(init_raw_ticker_data(latest_tick_for_equivalent, web_socket.ws_id))


def get_instrument_from_token(ws, instrument_token):
    return ws.token_map.get(instrument_token)


def get_equivalent_tick_from_token(ws, instrument_token):
    instrument = get_instrument_from_token(ws, instrument_token)
    equivalent_token = instrument.equivalent_token
    return get_latest_tick_by_instrument_token_from_global_cache(equivalent_token)


def add_buy_and_sell_task_to_queue(event):
    try:
        if remove_order_task_if_avl():
            remove_margin_or_throw_error(event["reqd_margin"])
            logging.info(f"Removed margin: {event['reqd_margin']:.2f} for opportunity of {event['trading_symbol']}")
            asyncio.run(consume_buy_or_sell_tasks(event))
        else:
            event["opportunity"].order_on_hold = True
            logging.info(f"Didn't remove any margin for opportunity of {event['trading_symbol']} due to full queue")
            add(event["opportunity"])
    except OrderException:
        event["opportunity"].low_margin_hold = True
        avl_margin = get_available_margin()
        logging.info(f"Available margin {avl_margin:.2f} < reqd margin {event['reqd_margin']:.2f} for opportunity of {event['trading_symbol']}")
        add(event["opportunity"])
    except Exception as e:
        add_margin(event["reqd_margin"])
        add_to_avl_order_task()
        logging.info(f"Added margin: {event['reqd_margin']:.2f} for opportunity of {event['trading_symbol']} "
                     f"upon exception while adding task to queue")
        log_info_and_notify("Error while adding task to queue: {} on process {}".format(e, os.getpid()))
