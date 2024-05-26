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
from ticker_service import is_ticker_valid
from order_service import realise_arbitrage_opportunity
from Models.web_socket import WebSocket
from arbitrage_service import check_arbitrage
from mysql_config import add_all, add
import time
from kiteconnect.utils import send_slack_message
from kiteconnect.login import get_kite_client_from_cache

logging.basicConfig(level=logging.DEBUG)


# Callback for tick reception.
def on_ticks(ws, ticks):
    if len(ticks.keys()) > 0:
        tokens = list(ws.token_map.keys())
        logging.info("websocket.{}.Received {} ticks for {} tokens".format(ws.ws_id, len(ticks.keys()), len(tokens)))

        process_start_time = datetime.now()
        num_of_opportunity = 0
        raw_tickers = []

        for instrument_token in list(ticks.keys()):
            latest_tick_for_instrument = ticks.get(instrument_token)
            instrument = ws.token_map.get(instrument_token)
            equivalent_token = instrument.equivalent_token
            latest_tick_for_equivalent = ws.latest_tick_map.get(equivalent_token)
            ws.latest_tick_map[instrument_token] = latest_tick_for_instrument

            if not is_ticker_valid(latest_tick_for_equivalent) or not is_ticker_valid(latest_tick_for_instrument):
                continue

            if ws.try_ordering:
                kite_client = get_kite_client_from_cache()
                available_holdings_for_instrument = kite_client.available_holdings[instrument_token]
                available_margin = kite_client.available_margin
                max_buy_quantity = min(available_holdings_for_instrument,
                                       available_margin / latest_tick_for_instrument['last_price'])
            else:
                max_buy_quantity = instrument.max_buy_value / latest_tick_for_instrument['last_price'] \
                    if latest_tick_for_instrument['last_price'] > 0 else 0

            opportunity = check_arbitrage(latest_tick_for_equivalent, latest_tick_for_instrument,
                                          instrument.threshold_percentage, instrument.buy_threshold,
                                          max_buy_quantity, ws.ws_id)
            if not opportunity:
                continue

            num_of_opportunity += 1

            if ws.try_ordering:
                opportunity = realise_arbitrage_opportunity(opportunity)

            add(opportunity)

            raw_tickers.append(init_raw_ticker_data(
                exchange_timestamp=latest_tick_for_instrument['exchange_timestamp'],
                instrument_token=latest_tick_for_instrument['instrument_token'],
                tradable=latest_tick_for_instrument['tradable'],
                last_price=latest_tick_for_instrument['last_price'],
                last_traded_quantity=latest_tick_for_instrument['last_traded_quantity'],
                last_trade_time=latest_tick_for_instrument['last_trade_time'],
                ticker_received_time=latest_tick_for_instrument['ticker_received_time'],
                depth=latest_tick_for_instrument['depth'],
                ws_id=ws.ws_id))

            raw_tickers.append(init_raw_ticker_data(
                exchange_timestamp=latest_tick_for_equivalent['exchange_timestamp'],
                instrument_token=latest_tick_for_equivalent['instrument_token'],
                tradable=latest_tick_for_equivalent['tradable'],
                last_price=latest_tick_for_equivalent['last_price'],
                last_traded_quantity=latest_tick_for_equivalent['last_traded_quantity'],
                last_trade_time=latest_tick_for_equivalent['last_trade_time'],
                ticker_received_time=latest_tick_for_equivalent['ticker_received_time'],
                depth=latest_tick_for_equivalent['depth'],
                ws_id=ws.ws_id))

        add_all(raw_tickers)

        logging.info("websocket.{}.Elapsed time: {}, had {} opportunities"
                     .format(ws.ws_id, datetime.now() - process_start_time, num_of_opportunity))


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
    logging.debug("websocket.{}.Order update : {}".format(ws.ws_id, data))


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
    while True:
        if count % 60 == 0:
            send_slack_message("Equalizer up and running")
        count += 1
        time.sleep(60)
    return None


def get_ws_id_to_web_socket_map():
    web_sockets = WebSocket.get_all_web_sockets()

    ws_id_to_socket_map = {}
    for web_socket in web_sockets:
        ws_id_to_socket_map[web_socket.ws_id] = web_socket

    return ws_id_to_socket_map
