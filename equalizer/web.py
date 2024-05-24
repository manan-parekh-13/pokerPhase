import os
import logging

from flask import Flask, jsonify, request, abort

from kiteconnect.login import login_via_enc_token_and_return_client, get_kite_client, login_via_two_f_a
from service.socket_service import init_kite_web_socket, send_web_socket_updates
from service.arbitrage_service import get_ws_id_to_token_to_instrument_map
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
        kite = login_via_two_f_a()

    if not kite.enc_token:
        send_slack_message("Unable to login")
        abort(500, "Unable to login")

    send_slack_message("Successfully logged in!")
    send_slack_message("enc_token: {}".format(kite.enc_token))

    ws_id_to_token_to_instrument_map = get_ws_id_to_token_to_instrument_map()

    for ws_id in ws_id_to_token_to_instrument_map.keys():
        sub_token_map = ws_id_to_token_to_instrument_map[ws_id]
        kws = init_kite_web_socket(kite, True, 3, sub_token_map, ws_id)
        # Infinite loop on the main thread.
        # You have to use the pre-defined callbacks to manage subscriptions.
        kws.connect(threaded=True)

    logging.info("This is main thread. Will send status updates in websocket every 1 hour.")
    # Block main thread
    send_web_socket_updates()
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
