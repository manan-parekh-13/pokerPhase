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
from kiteconnect import KiteTicker
from urllib.parse import quote
from datetime import datetime
from Models.raw_ticker_data import init_raw_ticker_data
from equalizer.service.ticker_service import is_ticker_valid, is_ticker_stale
from equalizer.service.order_service import realise_arbitrage_opportunity
from Models.order_info import init_order_info_from_order_update
from equalizer.service.arbitrage_service import check_arbitrage
from mysql_config import add_all, add
from equalizer.service.aggregate_service import get_new_aggregate_data_from_pre_value
import time
from kiteconnect.utils import log_info_and_notify, get_env_variable
from kiteconnect.global_cache import (get_kite_client_from_cache, get_latest_aggregate_data_for_ws_id_from_global_cache,
                                      get_latest_tick_by_instrument_token_from_global_cache,
                                      update_latest_ticks_for_instrument_tokens_in_bulk, is_order_on_hold_currently)
from equalizer.service.aggregate_service import save_latest_aggregate_data_from_cache


# Callback for tick reception.
def on_ticks(ws, ticks):
    if not ticks:
        return
    logging.debug("websocket.{}.Received {} ticks for {} tokens".format(ws.ws_id, len(ticks), len(ws.token_map)))

    raw_tickers = []
    kite_client = get_kite_client_from_cache()

    for instrument_token, latest_tick_for_instrument in ticks.items():
        latest_tick_for_equivalent = get_equivalent_tick_from_token(ws, instrument_token)

        if not is_ticker_valid(latest_tick_for_equivalent) or not is_ticker_valid(latest_tick_for_instrument):
            continue

        ltp = latest_tick_for_instrument['last_price']
        instrument = get_instrument_from_token(ws, instrument_token)

        if ws.try_ordering:
            margin_and_holdings = kite_client.get_available_margin_and_holdings_for_trading_symbol(instrument.trading_symbol)
            available_holdings = margin_and_holdings['available_holdings']
            available_margin = margin_and_holdings['available_margin']
            max_buy_quantity = min(available_holdings, available_margin / ltp)
        else:
            max_buy_quantity = int(get_env_variable('DEFAULT_MARGIN_FOR_CHECKING')) / ltp

        if max_buy_quantity == 0:
            continue

        opportunity = check_arbitrage(latest_tick_for_equivalent, latest_tick_for_instrument,
                                      instrument.threshold_spread_coef, instrument.min_profit_percent,
                                      instrument.product_type, max_buy_quantity, ws.ws_id)

        if not opportunity:
            continue

        if is_ticker_stale(latest_tick_for_instrument) or is_ticker_stale(latest_tick_for_equivalent):
            opportunity.is_stale = True

        if ws.try_ordering and not is_order_on_hold_currently() and not opportunity.is_stale:
            opportunity = realise_arbitrage_opportunity(opportunity, instrument.product_type)

        add(opportunity)

        raw_tickers.append(init_raw_ticker_data(latest_tick_for_instrument, ws.ws_id))
        raw_tickers.append(init_raw_ticker_data(latest_tick_for_equivalent, ws.ws_id))

    add_all(raw_tickers)


def analyze_data_on_ticks(ws, ticks):
    if not ticks:
        return
    logging.debug("websocket.{}.Received {} ticks for {} tokens".format(ws.ws_id, len(ticks), len(ws.token_map)))

    update_latest_ticks_for_instrument_tokens_in_bulk(ticks)

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


# Callback for successful connection.
def on_connect(ws, response):
    logging.info("websocket.{}.Successfully connected. Response: {}".format(ws.ws_id, response))
    tokens = list(ws.token_map.keys())
    ws.subscribe(tokens)
    ws.set_mode(ws.mode, tokens)
    logging.info("websocket.{}.Subscribe to tokens in {} mode: {}".format(ws.ws_id, ws.mode, tokens))


# Callback when current connection is closed.
def on_close(ws, code, reason):
    logging.info("websocket.{id}.Connection closed: {code} - {reason}".format(id=ws.ws_id, code=code, reason=reason))


# Callback when connection closed with error.
def on_error(ws, code, reason):
    logging.info("websocket.{id}.Connection error: {code} - {reason}".format(id=ws.ws_id, code=code, reason=reason))


# Callback when reconnect is on progress
def on_reconnect(ws, attempts_count):
    logging.info("websocket.{}.Reconnecting: {}".format(ws.ws_id, attempts_count))


# Callback when all reconnect failed (exhausted max retries)
def on_noreconnect(ws):
    logging.info("websocket.{}.Reconnect failed.".format(ws.ws_id))


def on_order_update(ws, data):
    logging.info("websocket.{}.Order update : {}".format(ws.ws_id, data))

    update_received_time = datetime.now()
    kite_client = get_kite_client_from_cache()

    data['received_time'] = update_received_time
    log_info_and_notify("Order update: {}".format(data))

    if data['status'] != kite_client.COMPLETE or data['status'] != kite_client.CANCELLED:
        # wait for it
        return

    initial_value = kite_client.get_available_margin_and_holdings_for_trading_symbol(data['tradingsymbol'])

    order_updates = {
        'instrument': data['tradingsymbol'],
        'received_time': update_received_time,
        'initial_margin': initial_value['available_margin'],
        'initial_holdings': initial_value['available_holdings'],
        'price': data['average_price'],
        'quantity': data['filled_quantity'],
        'type': '{} : {}'.format(data['transaction_type'], data['exchange'])
    }

    # update available margins and holdings
    latest_margins = kite_client.margins(segment=kite_client.MARGIN_EQUITY)

    if data['transaction_type'] == kite_client.TRANSACTION_TYPE_BUY:
        kite_client.set_new_margin(new_margin=latest_margins)
    else:
        kite_client.set_new_margins_and_remove_used_holdings(new_margins=latest_margins,
                                                             used_holdings=data['filled_quantity'],
                                                             trading_symbol=data['tradingsymbol'])

    final_value = kite_client.get_available_margin_and_holdings_for_instrument(data['tradingsymbol'])
    order_updates['final_margin'] = final_value['available_margin']
    order_updates['final_holdings'] = final_value['available_holdings']

    # save order info - todo @manan can be removed once we crack the zerodha's console
    # init_order_info_from_order_update(data, update_received_time)

    log_info_and_notify(order_updates)


def init_kite_web_socket(kite_client, debug, reconnect_max_tries, token_map, ws_id, try_ordering, is_data_ws):
    kws = KiteTicker(enc_token=quote(kite_client.enc_token), debug=debug, reconnect_max_tries=reconnect_max_tries,
                     token_map=token_map, ws_id=ws_id, try_ordering=try_ordering)

    # Assign the callbacks.
    kws.on_ticks = analyze_data_on_ticks if is_data_ws else on_ticks
    kws.on_close = on_close
    kws.on_error = on_error
    kws.on_connect = on_connect
    kws.on_reconnect = on_reconnect
    kws.on_noreconnect = on_noreconnect
    kws.on_order_update = on_order_update if try_ordering else None
    return kws


def send_web_socket_updates():
    count = 0
    # Block main thread
    while True:
        if count % 5 == 0 and count > 0:
            save_latest_aggregate_data_from_cache()
        count += 1
        time.sleep(60)
    return None


def get_instrument_from_token(ws, instrument_token):
    return ws.token_map.get(instrument_token)


def get_equivalent_tick_from_token(ws, instrument_token):
    instrument = get_instrument_from_token(ws, instrument_token)
    equivalent_token = instrument.equivalent_token
    return get_latest_tick_by_instrument_token_from_global_cache(equivalent_token)
