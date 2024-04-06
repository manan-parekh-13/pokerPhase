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

import time
import logging
from kiteconnect import KiteTicker
from urllib.parse import quote
from equalizer.service.ticker_service import save_ticker_data, are_all_tickers_recent
from equalizer.service.arbitrage_service import check_arbitrage


logging.basicConfig(level=logging.DEBUG)

# METROPOLIS BSE & NSE
latest_ticks = {2452737: None, 138918404: None}
# Max difference between current time and latest ticks acceptable for checking arbitrage
max_time_diff_in_sec = 10
# Min profit percentage required for ticker to be arbitrage opportunity
threshold_percentage = 0
# Min buy value required for arbitrage to be feasible
buy_threshold = 0

tokens = list(latest_ticks.keys())


def update_latest_tick(instrument_token, ticker):
    latest_ticks[instrument_token] = ticker


# Callback for tick reception.
def on_ticks(ws, ticks):
    if len(ticks) > 0:
        logging.info("Received {} ticks for {} tokens".format(len(ticks), len(tokens)))
        for tick in ticks:
            update_latest_tick(tick['instrument_token'], tick)
        all_recent = are_all_tickers_recent(latest_ticks, max_time_diff_in_sec)

        if all_recent:
            source1 = latest_ticks.keys()[0]
            source2 = latest_ticks.keys()[1]
            tick1 = latest_ticks.values()[0]
            tick2 = latest_ticks.values()[1]
            check_arbitrage(tick1, tick2, source1, source2, threshold_percentage, buy_threshold)
        save_ticker_data(ticks)


# Callback for successful connection.
def on_connect(ws, response):
    logging.info("Successfully connected. Response: {}".format(response))
    ws.subscribe(tokens)
    ws.set_mode(ws.MODE_FULL, tokens)
    logging.info("Subscribe to tokens in {} mode: {}".format(ws.MODE_FULL, tokens))


# Callback when current connection is closed.
def on_close(ws, code, reason):
    logging.info("Connection closed: {code} - {reason}".format(code=code, reason=reason))


# Callback when connection closed with error.
def on_error(ws, code, reason):
    logging.info("Connection error: {code} - {reason}".format(code=code, reason=reason))


# Callback when reconnect is on progress
def on_reconnect(ws, attempts_count):
    logging.info("Reconnecting: {}".format(attempts_count))


# Callback when all reconnect failed (exhausted max retries)
def on_noreconnect(ws):
    logging.info("Reconnect failed.")


def init_kite_web_socket(kite_client, debug, reconnect_max_tries):
    kws = KiteTicker(enc_token=quote(kite_client.enc_token), debug=debug, reconnect_max_tries=reconnect_max_tries)

    # Assign the callbacks.
    kws.on_ticks = on_ticks
    kws.on_close = on_close
    kws.on_error = on_error
    kws.on_connect = on_connect
    kws.on_reconnect = on_reconnect
    kws.on_noreconnect = on_noreconnect
    return kws


def update_web_socket(kws):
    count = 0
    # while True:
    #     count += 1
    #     if count == 4:
    #         if kws.is_connected():
    #             logging.info("### Closing websocket connection")
    #             kws._close(code=3001, reason="Terminal Count Achieved")
    #             break
    #     if count % 2 == 0:
    #         if kws.is_connected():
    #             logging.info("### Set mode to LTP for all tokens")
    #             kws.set_mode(kws.MODE_LTP, tokens)
    #     else:
    #         if kws.is_connected():
    #             logging.info("### Set mode to quote for all tokens")
    #             kws.set_mode(kws.MODE_QUOTE, tokens)
    #
    #     time.sleep(5)
    return None
