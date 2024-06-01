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
from equalizer.service.ticker_service import is_ticker_valid
from equalizer.service.order_service import realise_arbitrage_opportunity
from equalizer.service.charges_service import calc_transac_charges
from Models.web_socket import WebSocket
from Models.order_info import init_order_info_from_order_update
from equalizer.service.arbitrage_service import check_arbitrage
from mysql_config import add_all, add
import time
from kiteconnect.utils import log_and_notify, get_env_variable
from kiteconnect.login import get_kite_client_from_cache

logging.basicConfig(level=logging.DEBUG)


# Callback for tick reception.
def on_ticks(ws, ticks):
    if not ticks:
        return
    logging.debug("websocket.{}.Received {} ticks for {} tokens".format(ws.ws_id, len(ticks), len(ws.token_map)))

    process_start_time = datetime.now()
    raw_tickers = []
    kite_client = get_kite_client_from_cache()

    for instrument_token, latest_tick_for_instrument in ticks.items():
        # update latest tick map
        ws.latest_tick_map[instrument_token] = latest_tick_for_instrument

        latest_tick_for_equivalent = get_equivalent_tick_from_token(ws, instrument_token)

        if not is_ticker_valid(latest_tick_for_equivalent) or not is_ticker_valid(latest_tick_for_instrument):
            continue

        ltp = latest_tick_for_instrument['last_price']

        if ws.try_ordering:
            margin_and_holdings = kite_client.get_available_margin_and_holdings_for_instrument(instrument_token)
            available_holdings = margin_and_holdings['available_holdings']
            available_margin = margin_and_holdings['available_margin']
            max_buy_quantity = min(available_holdings, available_margin / ltp)
        else:
            max_buy_quantity = get_env_variable('DEFAULT_MARGIN_FOR_CHECKING') / ltp

        if max_buy_quantity == 0:
            continue

        instrument = get_instrument_from_token(ws, instrument_token)

        opportunity = check_arbitrage(latest_tick_for_equivalent, latest_tick_for_instrument,
                                      instrument.threshold_spread_coef, instrument.min_profit_percent,
                                      instrument.product_type, max_buy_quantity, ws.ws_id)
        if not opportunity:
            continue

        if ws.try_ordering:
            opportunity = realise_arbitrage_opportunity(opportunity, instrument.product_type)

        add(opportunity)

        raw_tickers.append(init_raw_ticker_data(latest_tick_for_instrument, ws.ws_id))
        raw_tickers.append(init_raw_ticker_data(latest_tick_for_equivalent, ws.ws_id))

    add_all(raw_tickers)
    logging.info("websocket.{}.Elapsed time: {}.".format(ws.ws_id, datetime.now() - process_start_time))


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
    initial_value = kite_client.get_available_margin_and_holdings_for_instrument(data['instrument_token'])

    order_updates = {
        'instrument': data['tradingsymbol'],
        'received_time': update_received_time,
        'initial_margin': initial_value['available_margin'],
        'initial_holdings': initial_value['available_holdings'],
        'price': data['average_price'],
        'quantity': data['filled_quantity'],
        'type': '{} : {} : {}'.format(data['transaction_type'], data['product'], data['exchange'])
    }

    # update available margins and holdings
    if data['status'] == kite_client.COMPLETE or data['status'] == kite_client.CANCELLED:
        if data['transaction_type'] == kite_client.TRANSACTION_TYPE_BUY:
            kite_client.remove_used_margin(used_margin=calc_transac_charges(
                order_value=data['filled_quantity'] * data['average_price'],
                product_type=data['product'],
                transaction_type=data['transaction_type']))
        else:
            kite_client.remove_used_margins_and_holdings(instrument_token=data['instrument_token'],
                                                         used_holdings=data['filled_quantity'],
                                                         used_margin=calc_transac_charges(
                order_value=data['filled_quantity'] * data['average_price'],
                product_type=data['product'],
                transaction_type=data['transaction_type']))

    final_value = kite_client.get_available_margin_and_holdings_for_instrument(data['instrument_token'])
    order_updates['final_margin'] = final_value['available_margin']
    order_updates['final_holdings'] = final_value['available_holdings']

    # save order info - todo @manan can be removed once we crack the zerodha's console
    init_order_info_from_order_update(data, update_received_time)

    log_and_notify(order_updates)


def init_kite_web_socket(kite_client, debug, reconnect_max_tries, token_map, ws_id, mode, try_ordering):
    kws = KiteTicker(enc_token=quote(kite_client.enc_token), debug=debug, reconnect_max_tries=reconnect_max_tries,
                     token_map=token_map, ws_id=ws_id, mode=mode, try_ordering=try_ordering)

    # Assign the callbacks.
    kws.on_ticks = on_ticks
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
        if count % 60 == 0:
            log_and_notify("Equalizer up and running")
        count += 1
        time.sleep(60)
    return None


def get_ws_id_to_web_socket_map():
    web_sockets = WebSocket.get_all_web_sockets()

    ws_id_to_socket_map = {}
    for web_socket in web_sockets:
        ws_id_to_socket_map[web_socket.ws_id] = web_socket

    return ws_id_to_socket_map


def get_instrument_from_token(ws, instrument_token):
    return ws.token_map.get(instrument_token)


def get_equivalent_tick_from_token(ws, instrument_token):
    instrument = get_instrument_from_token(ws, instrument_token)
    equivalent_token = instrument.equivalent_token
    return ws.latest_tick_map.get(equivalent_token)
