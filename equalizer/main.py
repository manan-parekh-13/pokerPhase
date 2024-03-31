import os
import logging
from datetime import date, datetime
from decimal import Decimal

from flask import Flask, jsonify, request, abort

from service.login import login_via_enc_token_and_return_client, get_kite_client, login_via_two_f_a, login
from service.threaded_ticker import init_kite_web_socket, update_web_socket

logging.basicConfig(level=logging.DEBUG)

# Base settings
PORT = 5010
HOST = "127.0.0.1"

def serializer(obj): return isinstance(obj, (date, datetime, Decimal)) and str(obj)  # noqa


# App
app = Flask(__name__)
app.secret_key = os.urandom(24)

# Templates
status_template = """
    <div>App is live on port - <b>{port}</b>.</div>
    <div>Request Id - <b>{request_id}</b>.</div>
    <div>Enc token - <b>{enc_token}</b>.</div>
    """


@app.route("/status")
def status():
    kite = get_kite_client();
    return status_template.format(
        port=PORT,
        request_id=kite.request_id,
        enc_token=kite.enc_token
    )


@app.route("/login/otp")
def login_via_otp():
    kite = login_via_two_f_a()
    if not kite.enc_token:
        abort(500, "Unable to verify otp / Token not fetched")

    return "Successfully logged in!"


@app.route("/login/enc_token", methods=['GET'])
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
        abort(500, "Unable to login")

    kws = init_kite_web_socket(kite, True, 3)

    # Infinite loop on the main thread.
    # You have to use the pre-defined callbacks to manage subscriptions.
    kws.connect(threaded=True)
    # Block main thread
    logging.info("This is main thread. Will change websocket mode every 5 seconds.")
    update_web_socket(kws)
    return "kind of worked"


@app.route("/holdings.json")
def holdings():
    kite = get_kite_client()
    return jsonify(holdings=kite.holdings())


if __name__ == "__main__":
    logging.info("Starting server: http://{host}:{port}".format(host=HOST, port=PORT))
    app.run(host=HOST, port=PORT, debug=True)
