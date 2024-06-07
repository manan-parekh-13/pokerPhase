from kiteconnect.utils import set_timezone_in_datetime
from kiteconnect.global_cache import get_kite_client_from_cache
from flask import abort
from datetime import datetime


def login_via_enc_token(enc_token):
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
