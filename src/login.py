import os
from kiteconnect.utils import get_sensitive_parameter, set_timezone_in_datetime
import logging
from datetime import date, datetime
from decimal import Decimal

from flask import Flask, jsonify, request, session, abort
from kiteconnect import KiteConnect

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


def get_kite_client(root=None):
    """Returns a kite client object
    """
    user_id = get_sensitive_parameter('USER_ID')
    password = get_sensitive_parameter('PASSWORD')
    kite = KiteConnect(debug=True, root=root, user_id=user_id, password=password)
    if "enc_token" in session:
        kite.set_enc_token_in_session(kite, session["enc_token"])
    if "request_id" in session:
        kite.set_request_id_in_session(kite, session["request_id"])
    return kite


@app.route("/status")
def status():
    kite = get_kite_client();
    return status_template.format(
        port=PORT,
        request_id=kite.request_id,
        enc_token=kite.enc_token
    )


@app.route("/login")
def login():

    kite = get_kite_client("https://kite.zerodha.com")
    if not kite.user_id:
        abort(500, "Invalid user_id.")

    if not kite.password:
        abort(500, "Invalid password.")

    kite.generate_request_id()

    if not kite.request_id:
        abort(500, "Couldn't generate request for login")

    otp_sent_timestamp = set_timezone_in_datetime(datetime.now())

    kite.generate_otp_for_login_request()

    otp = kite.return_latest_otp_later_than(otp_sent_timestamp)

    if not otp:
        abort(500, "Unable to fetch otp")

    kite.verify_otp_for_request_id(otp)

    if not kite.enc_token:
        abort(500, "Unable to verify otp / Token not fetched")

    return "Successfully logged in!"


@app.route("/login/enctoken", methods=['GET'])
def login_via_enc_token():
    enc_token = request.form.get('enc_token')
    kite = get_kite_client()
    kite.set_enc_token_in_session(kite, enc_token)
    if not kite.enc_token:
        abort(500, "Unable to set enc token")

    return "Successfully logged in via enc token"


@app.route("/holdings.json")
def holdings():
    kite = get_kite_client()
    return jsonify(holdings=kite.holdings())


@app.route("/orders.json")
def orders():
    kite = get_kite_client()
    return jsonify(orders=kite.orders())


if __name__ == "__main__":
    logging.info("Starting server: http://{host}:{port}".format(host=HOST, port=PORT))
    app.run(host=HOST, port=PORT, debug=True)
