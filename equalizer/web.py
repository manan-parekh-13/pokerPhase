import os
import logging
import datetime
import time

from flask import Flask, jsonify, request, abort, session

from kiteconnect.login import login_via_enc_token_and_return_client, get_kite_client, login_via_two_f_a, login
from service.socket_service import init_kite_web_socket, update_web_socket
from service.arbitrage_service import get_instrument_token_map_for_arbitrage
from environment.loader import load_environment
from mysql_config import add_all
from Models import instrument
from kiteconnect.utils import send_slack_message

logging.basicConfig(level=logging.DEBUG)

# Base settings
PORT = 5010
HOST = "127.0.0.1"

# Load the environment configuration
environment = os.getenv('FLASK_ENV')
load_environment(environment)

# App
app = Flask(__name__)
app.secret_key = 'hello'

# Templates
status_template = """
    <div>App is live on port - <b>{port}</b>.</div>
    <div>Request Id - <b>{request_id}</b>.</div>
    <div>Enc token - <b>{enc_token}</b>.</div>
    <div>Web Sockets - <b>{web_sockets}</b>.</div>
    """


@app.route("/status", methods=['GET'])
def status():
    kite = get_kite_client();
    return status_template.format(
        port=PORT,
        request_id=kite.request_id,
        enc_token=kite.enc_token,
        web_sockets=kite.web_sockets,
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
    kite = get_kite_client()
    if not kite.enc_token:
        enc_token = request.form.get('enc_token')
        kite = login(enc_token)

    if not kite.enc_token:
        send_slack_message("Unable to login")
        abort(500, "Unable to login")

    send_slack_message("Successfully logged in!")
    send_slack_message("enc_token: {}".format(kite.enc_token))
    send_slack_message("session_id: {}".format(session.get('session_id')))

    token_map = get_instrument_token_map_for_arbitrage()

    start_index = 0
    max_tokens_per_socket = kite.max_tokens_per_socket
    web_socket_meta = []

    market_start_time = datetime.time(9, 30, 0)
    market_end_time = datetime.time(15, 30, 0)

    sorted_token_list = sorted(token_map.items())

    ws_id_to_socket_map = {}

    while start_index < len(sorted_token_list):
        end_index = min(start_index + max_tokens_per_socket, len(sorted_token_list) - 1)
        sub_token_map = dict(sorted_token_list[start_index:end_index])
        ws_id = int(start_index / max_tokens_per_socket)
        kws = init_kite_web_socket(kite, True, 3, sub_token_map, ws_id, market_end_time, market_start_time)
        # Infinite loop on the main thread.
        # You have to use the pre-defined callbacks to manage subscriptions.
        kws.connect(threaded=True)
        ws_id_to_socket_map[ws_id] = kws
        web_socket_meta.append({
            "ws_id": ws_id,
            "count": end_index - start_index + 1,
            "start_index": start_index,
            "end_index": end_index,
        })
        start_index += max_tokens_per_socket

    kite.set_web_sockets_in_session(kite, web_socket_meta)
    logging.info("This is main thread. Will look out for any updates in websocket every 60 seconds.")
    # let the web sockets try connection, wait before updating them
    time.sleep(60)
    # Block main thread
    update_web_socket(ws_id_to_socket_map)
    return "kind of worked"


@app.route("/holdings.json", methods=['GET'])
def holdings():
    kite = get_kite_client()
    return jsonify(holdings=kite.holdings())


@app.route("/instruments.json", methods=['GET'])
def instruments():
    kite = get_kite_client()
    instrument_records = kite.instruments()
    instrument_model_list = instrument.convert_all(instrument_records)
    add_all(instrument_model_list)
    return jsonify(instrument_records)


if __name__ == "__main__":
    logging.info("Starting server: http://{host}:{port}".format(host=HOST, port=PORT))
    app.run(host=HOST, port=PORT, debug=True)
