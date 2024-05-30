from kiteconnect.utils import get_sensitive_parameter, set_timezone_in_datetime
from kiteconnect import KiteConnect
from flask import abort
from datetime import datetime

global_cache = {}


def get_kite_client(root=None, debug=False):
    """Returns a kite client object
    """
    user_id = get_sensitive_parameter('USER_ID')
    if not user_id:
        abort(500, "Invalid user_id.")

    password = get_sensitive_parameter('PASSWORD')
    if not password:
        abort(500, "Invalid password.")

    return KiteConnect(debug=debug, root=root, user_id=user_id, password=password)


def get_kite_client_from_cache():
    if "kite_client" in global_cache:
        return global_cache.get("kite_client")
    kite = get_kite_client()
    global_cache['kite_client'] = kite
    return kite


def login_via_enc_token_and_return_client(enc_token):
    kite = get_kite_client_from_cache()
    kite.set_enc_token(enc_token)
    return kite


def login_via_two_f_a():
    kite = get_kite_client_from_cache()
    # delete existing value of enc_token if any
    kite.expire_current_enc_token()
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
