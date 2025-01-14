###############################################################################
#
# The MIT License (MIT)
#
# Copyright (c) Zerodha Technology Pvt. Ltd.
#
# This example shows how to run KiteTicker in threaded mode.
# KiteTicker runs in seprate thread and main thread is blocked to juggle between
# different modes for current subscribed tokens. In real world web apps
# the main thread will be your web server and you can access WebSocket object
# in your main thread while running KiteTicker in separate thread.
###############################################################################
import logging

from equalizer.service.positions_service import get_instrument_wise_positions
from kiteconnect import KiteTicker
from urllib.parse import quote
from datetime import datetime
import threading
import asyncio
from Models.raw_ticker_data import init_raw_ticker_data
from Models.arbitrage_opportunity import ArbitrageOpportunity
from equalizer.service.arbitrage_service import check_arbitrage
from mysql_config import add_all, add
from equalizer.service.aggregate_service import get_new_aggregate_data_from_pre_value
from kiteconnect.utils import log_info_and_notify, get_env_variable, datetime_to_str, dict_to_string, \
    get_product_type_from_ws_id
from kiteconnect.global_stuff import (get_kite_client_from_cache, get_latest_aggregate_data_for_ws_id_from_global_cache,
                                      get_latest_tick_by_instrument_token_from_global_cache,
                                      update_latest_ticks_for_instrument_tokens_in_bulk,
                                      add_buy_and_sell_task_to_queue)
from equalizer.service.aggregate_service import save_latest_aggregate_data_from_cache


# Callback for tick reception.
def on_ticks(ws, ticks):
    if not ticks:
        return
    update_latest_ticks_for_instrument_tokens_in_bulk(ticks)

    logging.debug("websocket.{}.process_thread {}.Received {} ticks for {} tokens"
                  .format(ws.ws_id, threading.current_thread().name, len(ticks), len(ws.token_map)))

    raw_tickers = []
    kite_client = get_kite_client_from_cache()

    for instrument_token, latest_tick_for_instrument in ticks.items():
        opportunity_check_started_at = datetime.now()

        latest_tick_for_equivalent = get_equivalent_tick_from_token(ws, instrument_token)

        if not latest_tick_for_equivalent:
            continue

        ltp = latest_tick_for_instrument['depth']['sell'][0]['price']

        if ltp == 0.0:
            continue

        instrument = get_instrument_from_token(ws, instrument_token)

        if ws.try_ordering:
            available_margin = kite_client.get_available_margin()
            max_buy_quantity = available_margin / ltp
        else:
            max_buy_quantity = int(get_env_variable('DEFAULT_MARGIN_FOR_CHECKING')) / ltp

        if max_buy_quantity == 0:
            continue

        opportunity = check_arbitrage(latest_tick_for_equivalent, latest_tick_for_instrument,
                                      instrument.threshold_spread_coef, instrument.min_profit_percent,
                                      instrument.product_type, max_buy_quantity, ws.ws_id)

        if not opportunity:
            continue

        opportunity.opportunity_check_started_at = opportunity_check_started_at
        instrument.leverage = instrument.leverage if instrument.leverage else 1

        if not ws.try_ordering:
            add(opportunity)
            continue

        add_buy_and_sell_task_to_queue({
            "opportunity": opportunity,
            "product_type": get_product_type_from_ws_id(opportunity.ws_id),
            "reqd_margin": (opportunity.buy_price + opportunity.sell_price) * opportunity.quantity / instrument.leverage,
            "leverage": instrument.leverage
        })
        raw_tickers.append(init_raw_ticker_data(latest_tick_for_instrument, ws.ws_id))
        raw_tickers.append(init_raw_ticker_data(latest_tick_for_equivalent, ws.ws_id))

    add_all(raw_tickers)


def analyze_data_on_ticks(ws, ticks):
    if not ticks:
        return
    update_latest_ticks_for_instrument_tokens_in_bulk(ticks)

    start_time = datetime.now().timestamp()
    logging.debug("websocket.{}.process_thread {}.Received {} ticks for {} tokens"
                  .format(ws.ws_id, threading.current_thread().name, len(ticks), len(ws.token_map)))

    latest_aggregate_data = get_latest_aggregate_data_for_ws_id_from_global_cache(ws.ws_id)
    for instrument_token, latest_tick_for_instrument in ticks.items():
        if instrument_token in latest_aggregate_data:
            prev_ticker_for_instrument = latest_aggregate_data.get(instrument_token)
            latest_aggregate_data[instrument_token] = get_new_aggregate_data_from_pre_value(prev_ticker_for_instrument)
        else:
            latest_aggregate_data[instrument_token] = {
                'ticker_time': datetime.now().timestamp(),
                'started_at': datetime.now()
            }

    time_diff = datetime.now().timestamp() - start_time
    logging.debug("websocket.{}.process_thread {}.Processed {} ticks in {} seconds"
                  .format(ws.ws_id, threading.current_thread().name, len(ticks), time_diff))


# Callback for successful connection.
def on_connect(ws, response):
    logging.info("websocket.{}.process_thread {}.Successfully connected. Response: {}"
                 .format(ws.ws_id, threading.current_thread().name, response))
    tokens = list(ws.token_map.keys())
    ws.subscribe(tokens)
    ws.set_mode(ws.mode, tokens)
    logging.info("websocket.{}.process_thread {}.Subscribe to tokens in {} mode: {}"
                 .format(ws.ws_id, threading.current_thread().name, ws.mode, tokens))


# Callback when current connection is closed.
def on_close(ws, code, reason):
    logging.info("websocket.{id}.process_thread {thread}.Connection closed: {code} - {reason}"
                 .format(id=ws.ws_id, thread=threading.current_thread().name, code=code, reason=reason))


# Callback when connection closed with error.
def on_error(ws, code, reason):
    logging.info("websocket.{id}.process_thread {thread}.Connection error: {code} - {reason}"
                 .format(id=ws.ws_id, thread=threading.current_thread().name, code=code, reason=reason))


# Callback when reconnect is on progress
def on_reconnect(ws, attempts_count):
    logging.info("websocket.{}.process_thread {}.Reconnecting: {}"
                 .format(ws.ws_id, threading.current_thread().name, attempts_count))


# Callback when all reconnect failed (exhausted max retries)
def on_noreconnect(ws):
    logging.info("websocket.{}.process_thread {}.Reconnect failed.".format(ws.ws_id, threading.get_ident()))


def on_order_update(ws, data):
    logging.info("websocket.{}.process_thread {}.Order id : {} and status: {}".format(
        ws.ws_id, threading.current_thread().name, data['order_id'], data['status']))

    update_received_time = datetime.now()
    kite_client = get_kite_client_from_cache()

    if data['status'] != kite_client.COMPLETE and data['status'] != kite_client.CANCELLED:
        return

    initial_value = kite_client.get_available_margin_and_positions_for_trading_symbol_exchange(
        data['tradingsymbol'], data['exchange'])

    order_updates = {
        'instrument': f"{data['exchange']}_{data['tradingsymbol']}",
        'received_time': datetime_to_str(update_received_time),
        'initial_margin': initial_value['available_margin'],
        'initial_positions': initial_value['open_positions'],
        'price': data['average_price'],
        'quantity': data['filled_quantity'],
        'type': data['transaction_type']
    }

    # update available margins and positions
    latest_margins = kite_client.margins(segment=kite_client.MARGIN_EQUITY)
    latest_positions = get_instrument_wise_positions()

    kite_client.set_available_margin_and_positions(new_margins=latest_margins.get('net'), new_positions=latest_positions)

    final_value = kite_client.get_available_margin_and_positions_for_trading_symbol_exchange(
        data['tradingsymbol'], data['exchange'])
    order_updates['final_margin'] = final_value['available_margin']
    order_updates['final_positions'] = final_value['open_positions']

    log_info_and_notify("Order update: \n{}".format(dict_to_string(order_updates)))


def init_kite_web_socket(kite_client, debug, reconnect_max_tries, token_map, ws_id, try_ordering, is_data_ws):
    trading_symbol_map = {}

    for token, instrument in token_map.items():
        if instrument.trading_symbol in trading_symbol_map:
            continue
        trading_symbol_map[instrument.trading_symbol] = True

    kws = KiteTicker(enc_token=quote(kite_client.enc_token), debug=debug, reconnect_max_tries=reconnect_max_tries,
                     token_map=token_map, ws_id=ws_id, try_ordering=try_ordering, trading_symbol_map=trading_symbol_map)

    # Assign the callbacks.
    kws.on_ticks = analyze_data_on_ticks if is_data_ws else on_ticks
    kws.on_close = on_close
    kws.on_error = on_error
    kws.on_connect = on_connect
    kws.on_reconnect = on_reconnect
    kws.on_noreconnect = on_noreconnect
    kws.on_order_update = on_order_update if try_ordering else None
    return kws


async def send_web_socket_updates():
    while True:
        save_latest_aggregate_data_from_cache()
        latest_opportunity = ArbitrageOpportunity.get_latest_arbitrage_opportunity_by_id()
        if not latest_opportunity:
            log_info_and_notify("No opportunity found!")
        else:
            log_info_and_notify("Latest opportunity at {}".format(latest_opportunity.created_at))
        await asyncio.sleep(60 * 60)


def get_instrument_from_token(ws, instrument_token):
    return ws.token_map.get(instrument_token)


def get_equivalent_tick_from_token(ws, instrument_token):
    instrument = get_instrument_from_token(ws, instrument_token)
    equivalent_token = instrument.equivalent_token
    return get_latest_tick_by_instrument_token_from_global_cache(equivalent_token)
