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
from Models.raw_ticker_data import RawTickerData
from equalizer.service.ticker_service import is_ticker_valid
from equalizer.service.arbitrage_service import check_arbitrage
from mysql_config import add_all, add

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
                raw_tickers.append(RawTickerData(**latest_tick_for_instrument))
                raw_tickers.append(RawTickerData(**latest_tick_for_equivalent))

        add_all(raw_tickers)
        # kill the web socket in case time is past end_time
        if datetime.now().time() > ws.end_time:
            logging.info("### Closing websocket connection")
            ws._close(code=3001, reason="Time up")
            ws.stop_retry()
        logging.info("websocket.{}.Elapsed time: {}, had {} opportunities"
                     .format(ws.ws_id, datetime.now().time() - start_time, num_of_opportunity))


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


def init_kite_web_socket(kite_client, debug, reconnect_max_tries, token_map, ws_id, end_time):
    kws = KiteTicker(enc_token=quote(kite_client.enc_token), debug=debug, reconnect_max_tries=reconnect_max_tries,
                     token_map=token_map, ws_id=ws_id, end_time=end_time)

    # Assign the callbacks.
    kws.on_ticks = on_ticks
    kws.on_close = on_close
    kws.on_error = on_error
    kws.on_connect = on_connect
    kws.on_reconnect = on_reconnect
    kws.on_noreconnect = on_noreconnect
    return kws


def update_web_socket():
    # count = 0
    # while True:
    #     count += 1
    #     if count == 4:
    #         if kws.is_connected():
    #             logging.info("### Closing websocket connection")
    #             kws._close(code=3001, reason="Terminal Count Achieved")
    #             kws.stop_retry()
    #             break
    #     time.sleep(5)
    return None
