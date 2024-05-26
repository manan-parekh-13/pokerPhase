from kiteconnect.utils import get_sensitive_parameter, set_timezone_in_datetime
from kiteconnect import KiteConnect
from flask import session, abort
from datetime import datetime


def get_kite_client(root=None, debug=False):
    """Returns a kite client object
    """
    user_id = get_sensitive_parameter('USER_ID')
    if not user_id:
        abort(500, "Invalid user_id.")

    password = get_sensitive_parameter('PASSWORD')
    if not password:
        abort(500, "Invalid password.")

    kite = KiteConnect(debug=debug, root=root, user_id=user_id, password=password)
    if "enc_token" in session:
        kite.set_enc_token_in_session(kite, session["enc_token"])
    if "request_id" in session:
        kite.set_request_id_in_session(kite, session["request_id"])
    return kite


def login_via_enc_token_and_return_client(enc_token):
    kite = get_kite_client()
    kite.set_enc_token_in_session(kite, enc_token)
    return kite


def login_via_two_f_a():
    kite = get_kite_client()
    # delete existing value of enc_token if any
    kite.expire_current_session()
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
