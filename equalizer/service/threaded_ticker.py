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
from equalizer.service.ticker_service import save_ticker_data, is_ticker_valid
from equalizer.service.arbitrage_service import check_arbitrage, save_arbitrage_opportunities

logging.basicConfig(level=logging.DEBUG)


# Callback for tick reception.
def on_ticks(ws, ticks):
    if len(ticks.keys()) > 0:
        tokens = list(ws.token_map.keys())
        logging.info("Received {} ticks for {} tokens".format(len(ticks.keys()), len(tokens)))

        for instrument_token in list(ticks.keys()):
            latest_tick_for_instrument = ticks.get(instrument_token)
            instrument = ws.token_map.get(instrument_token)
            equivalent_token = instrument.equivalent_token
            latest_tick_for_equivalent = ws.latest_tick_map.get(equivalent_token)

            if is_ticker_valid(latest_tick_for_equivalent) and is_ticker_valid(latest_tick_for_instrument):
                opportunities = check_arbitrage(latest_tick_for_equivalent, latest_tick_for_instrument,
                                                instrument.threshold_percentage, instrument.buy_threshold)
                save_arbitrage_opportunities(opportunities)
            ws.latest_tick_map[instrument_token] = latest_tick_for_instrument

        save_ticker_data(ticks.values())


# Callback for successful connection.
def on_connect(ws, response):
    logging.info("Successfully connected. Response: {}".format(response))
    tokens = list(ws.token_map.keys())
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


def init_kite_web_socket(kite_client, debug, reconnect_max_tries, token_map):
    kws = KiteTicker(enc_token=quote(kite_client.enc_token), debug=debug, reconnect_max_tries=reconnect_max_tries, token_map=token_map)

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
