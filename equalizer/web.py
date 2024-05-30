import os
import logging
import json

from flask import Flask, jsonify, request, abort

from kiteconnect.login import (login_via_enc_token_and_return_client, login_via_two_f_a, get_kite_client_from_cache,
                               global_cache)
from service.socket_service import init_kite_web_socket, send_web_socket_updates, get_ws_id_to_web_socket_map
from service.arbitrage_service import get_ws_id_to_token_to_instrument_map
from service.instrument_service import get_token_to_arbitrage_instrument_map
from environment.loader import load_environment
from mysql_config import add_all
from Models import instrument
from Models.holdings import Holdings
from kiteconnect.utils import send_slack_message
from service.holding_service import get_holdings_available_for_arbitrage_in_map

logging.basicConfig(level=logging.DEBUG)

# Base settings
PORT = 5010
HOST = "127.0.0.1"

# Load the environment configuration
environment = os.getenv('FLASK_ENV')
load_environment(environment)


# App
app = Flask(__name__)
app.secret_key = 'Yo'

# Templates
status_template = """
    <div>App is live on port - <b>{port}</b>.</div>
    <div>Request Id - <b>{request_id}</b>.</div>
    <div>Enc token - <b>{enc_token}</b>.</div>
    """


@app.route("/status", methods=['GET'])
def status():
    kite = get_kite_client_from_cache();
    return status_template.format(
        port=PORT,
        request_id=kite.request_id,
        enc_token=kite.enc_token,
    )


@app.route("/login/otp", methods=['POST'])
def login_via_otp():
    kite = login_via_two_f_a()
    if not kite.enc_token:
        abort(500, "Unable to verify otp / Token not fetched")

    return "Successfully logged in!"


@app.route("/login/enc_token", methods=['POST'])
def login_via_enc_token():
    enc_token = request.form.get('enc_token')
    kite = login_via_enc_token_and_return_client(enc_token)
    if not kite.enc_token:
        abort(500, "Unable to set enc token")

    return "Successfully logged in via enc token"


@app.route("/equalizer/startup", methods=['POST'])
def start_up_equalizer():
    kite = get_kite_client_from_cache()
    if not kite.enc_token:
        kite = login_via_two_f_a()

    if not kite.enc_token:
        send_slack_message("Unable to login")
        abort(500, "Unable to login")

    send_slack_message("Successfully logged in!")
    send_slack_message("enc_token: {}".format(kite.enc_token))

    # cache instrument details for further use
    token_to_arbitrage_instrument_map = get_token_to_arbitrage_instrument_map()
    global_cache['instrument_map'] = token_to_arbitrage_instrument_map

    # get and set available margin and holdings in global cache
    usable_margin = request.form.get('usable_margin')
    available_holdings_map = get_holdings_available_for_arbitrage_in_map()
    kite.set_available_margin_and_holdings(new_margins=usable_margin, new_holdings=available_holdings_map)

    send_slack_message("Available margin: ".format(usable_margin))
    send_slack_message("Available holdings: ".format(available_holdings_map))

    # prepare web socket wise token map
    ws_id_to_token_to_instrument_map = get_ws_id_to_token_to_instrument_map()

    # get web socket meta
    ws_id_to_web_socket_map = get_ws_id_to_web_socket_map()

    for ws_id in ws_id_to_token_to_instrument_map.keys():
        sub_token_map = ws_id_to_token_to_instrument_map[ws_id]
        web_socket = ws_id_to_web_socket_map[ws_id]

        if web_socket.try_ordering and (not usable_margin or usable_margin <= 0):
            send_slack_message("Ordering not possible for ws_id {} as no margins available")
            continue

        if web_socket.try_ordering and (not available_holdings_map):
            send_slack_message("Ordering not possible for ws_id {} as no holdings available")
            continue

        kws = init_kite_web_socket(kite, True, 3, sub_token_map, ws_id,
                                   web_socket.mode, web_socket.try_ordering)
        # Infinite loop on the main thread.
        # You have to use the pre-defined callbacks to manage subscriptions.
        kws.connect(threaded=True)

    logging.info("This is main thread. Will send status of each websocket every 1 hour.")
    # Block main thread
    send_web_socket_updates()
    return "kind of worked"


@app.route("/holdings.json", methods=['GET'])
def holdings():
    kite = get_kite_client_from_cache()
    response = kite.holdings()
    if response:
        holding_list = []
        for holding in response:
            holding['arbitrage_quantity'] = None
            holding['authorisation'] = json.dumps(holding['authorisation'])
            holding_list.append(Holdings(**holding))
        add_all(holding_list)
    return jsonify(response)


@app.route("/margins.json", methods=['GET'])
def margins():
    kite = get_kite_client_from_cache()
    margin_resp = kite.margins()
    return jsonify(margin_resp)


@app.route("/instruments.json", methods=['GET'])
def instruments():
    kite = get_kite_client_from_cache()
    instrument_records = kite.instruments()
    instrument_model_list = instrument.convert_all(instrument_records)
    add_all(instrument_model_list)
    return jsonify(instrument_records)


if __name__ == "__main__":
    logging.info("Starting server: http://{host}:{port}".format(host=HOST, port=PORT))
    app.run(host=HOST, port=PORT, debug=True)
