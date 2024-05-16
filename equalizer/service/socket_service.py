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
from datetime import datetime, timedelta
from Models.raw_ticker_data import init_raw_ticker_data
from equalizer.service.ticker_service import is_ticker_valid
from equalizer.service.arbitrage_service import check_arbitrage
from mysql_config import add_all, add
from flask import session
import time

logging.basicConfig(level=logging.DEBUG)


# Callback for tick reception.
def on_ticks(ws, ticks):
    if len(ticks.keys()) > 0:
        tokens = list(ws.token_map.keys())
        logging.info("websocket.{}.Received {} ticks for {} tokens".format(ws.ws_id, len(ticks.keys()), len(tokens)))

        start_time = datetime.now().time()
        num_of_opportunity = 0
        raw_tickers = []

        for instrument_token in list(ticks.keys()):
            latest_tick_for_instrument = ticks.get(instrument_token)
            instrument = ws.token_map.get(instrument_token)
            equivalent_token = instrument.equivalent_token
            latest_tick_for_equivalent = ws.latest_tick_map.get(equivalent_token)
            ws.latest_tick_map[instrument_token] = latest_tick_for_instrument

            if is_ticker_valid(latest_tick_for_equivalent) and is_ticker_valid(latest_tick_for_instrument):
                opportunity = check_arbitrage(latest_tick_for_equivalent, latest_tick_for_instrument,
                                              instrument.threshold_percentage, instrument.buy_threshold,
                                              instrument.max_buy_value)
                if not opportunity:
                    continue
                num_of_opportunity += 1
                add(opportunity)

                raw_tickers.append(init_raw_ticker_data(
                    exchange_timestamp=latest_tick_for_instrument['exchange_timestamp'],
                    instrument_token=latest_tick_for_instrument['instrument_token'],
                    tradable=latest_tick_for_instrument['tradable'],
                    last_price=latest_tick_for_instrument['last_price'],
                    last_traded_quantity=latest_tick_for_instrument['last_traded_quantity'],
                    last_trade_time=latest_tick_for_instrument['last_trade_time'],
                    ticker_received_time=latest_tick_for_instrument['ticker_received_time'],
                    depth=latest_tick_for_instrument['depth']))

                raw_tickers.append(init_raw_ticker_data(
                    exchange_timestamp=latest_tick_for_equivalent['exchange_timestamp'],
                    instrument_token=latest_tick_for_equivalent['instrument_token'],
                    tradable=latest_tick_for_equivalent['tradable'],
                    last_price=latest_tick_for_equivalent['last_price'],
                    last_traded_quantity=latest_tick_for_equivalent['last_traded_quantity'],
                    last_trade_time=latest_tick_for_equivalent['last_trade_time'],
                    ticker_received_time=latest_tick_for_equivalent['ticker_received_time'],
                    depth=latest_tick_for_equivalent['depth']))

        add_all(raw_tickers)
        # kill the web socket in case time is past end_time
        if datetime.now().time() > ws.end_time:
            logging.info("### Closing websocket connection with id {}. Time is up".format(ws.ws_id))
            ws._close(code=3001, reason="Time up")
            ws.stop_retry()
        # kill the web socket in case time is not yet started
        if datetime.now().time() < ws.start_time:
            logging.info("### Closing websocket connection with id {}. Time is not yet started".format(ws.ws_id))
            ws._close(code=3001, reason="Time is not yet started")
            ws.stop_retry()

        end_time = datetime.now().time()
        time_difference = (timedelta(hours=end_time.hour, minutes=end_time.minute, seconds=end_time.second,
                                    microseconds=end_time.microsecond) -
                           timedelta(hours=start_time.hour, minutes=start_time.minute, seconds=start_time.second,
                                     microseconds=start_time.microsecond))
        logging.info("websocket.{}.Elapsed time: {}, had {} opportunities"
                     .format(ws.ws_id, time_difference, num_of_opportunity))


# Callback for successful connection.
def on_connect(ws, response):
    logging.info("websocket.{}.Successfully connected. Response: {}".format(ws.ws_id, response))
    tokens = list(ws.token_map.keys())
    ws.subscribe(tokens)
    ws.set_mode(ws.MODE_FULL, tokens)
    logging.info("websocket.{}.Subscribe to tokens in {} mode: {}".format(ws.ws_id, ws.MODE_FULL, tokens))


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


def init_kite_web_socket(kite_client, debug, reconnect_max_tries, token_map, ws_id, end_time, start_time):
    kws = KiteTicker(enc_token=quote(kite_client.enc_token), debug=debug, reconnect_max_tries=reconnect_max_tries,
                     token_map=token_map, ws_id=ws_id, end_time=end_time, start_time=start_time)

    # Assign the callbacks.
    kws.on_ticks = on_ticks
    kws.on_close = on_close
    kws.on_error = on_error
    kws.on_connect = on_connect
    kws.on_reconnect = on_reconnect
    kws.on_noreconnect = on_noreconnect
    return kws


def execute_change(socket_id, socket_info, change):
    # Implement your logic to execute the change here
    logging.info(f"Change detected for socket ID {socket_id}: {change}")


def update_web_socket(ws_id_to_socket_map):
    # let the web sockets try connection
    # wait before checking if connected
    time.sleep(60)
    while True:
        num_of_disconnected_sockets = 0
        for socket_id, kws in ws_id_to_socket_map.items():
            # with session.lock:
            if not kws.is_connected():
                logging.info("Socket {} disconnected".format(socket_id))
                num_of_disconnected_sockets += 1
                continue
            if 'socket_changes' not in session:
                logging.info("No change detected")
                continue
            if socket_id in session.socket_changes:
                change = session.socket_changes.pop(socket_id)
            if change is None:
                logging.info("No change detected")
            execute_change(socket_id, kws, change)
        if num_of_disconnected_sockets == len(ws_id_to_socket_map):
            logging.info("All sockets disconnected")
            break
        time.sleep(60)
    return None
