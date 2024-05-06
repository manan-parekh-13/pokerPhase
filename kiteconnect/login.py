from kiteconnect.utils import get_sensitive_parameter, set_timezone_in_datetime
from kiteconnect import KiteConnect
from flask import session, abort
from datetime import datetime


def get_kite_client(root=None, debug=False, max_tokens_per_socket=500):
    """Returns a kite client object
    """
    user_id = get_sensitive_parameter('USER_ID')
    if not user_id:
        abort(500, "Invalid user_id.")

    password = get_sensitive_parameter('PASSWORD')
    if not password:
        abort(500, "Invalid password.")

    kite = KiteConnect(debug=debug, root=root, user_id=user_id, password=password,
                       max_tokens_per_socket=max_tokens_per_socket)
    if "enc_token" in session:
        kite.set_enc_token_in_session(kite, session["enc_token"])
    if "request_id" in session:
        kite.set_request_id_in_session(kite, session["request_id"])
    if "web_sockets" in session:
        kite.set_web_sockets_in_session(kite, session["web_sockets"])
    return kite


def login_via_enc_token_and_return_client(enc_token):
    kite = get_kite_client()
    kite.set_enc_token_in_session(kite, enc_token)
    return kite


def login_via_two_f_a():
    kite = get_kite_client("https://kite.zerodha.com")

    kite.generate_request_id()
    if not kite.request_id:
        abort(500, "Couldn't generate request for login")

    otp_sent_timestamp = set_timezone_in_datetime(datetime.now())
    kite.generate_otp_for_login_request()

    otp = kite.return_latest_otp_later_than(otp_sent_timestamp)
    if not otp:
        abort(500, "Unable to fetch otp")

    kite.verify_otp_for_request_id(otp)
    return kite


def login(enc_token):
    if not enc_token:
        return login_via_two_f_a()
    else:
        return login_via_enc_token_and_return_client(enc_token)
