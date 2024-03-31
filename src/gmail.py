from utils import get_sensitive_parameter, convert_str_to_datetime, set_timezone_in_datetime, truncate_microseconds
import requests
import json
import time
from datetime import datetime


def get_latest_otp_from_mail():
    gmail_api_key = get_sensitive_parameter('GMAIL_API_KEY')
    gmail_api_path = get_sensitive_parameter('GMAIL_API_PATH')

    params = {
        "label": "zerodha-otp",
        "passkey": gmail_api_key
    }

    response = requests.get(gmail_api_path, params=params)

    if response.status_code == 200:
        meta_obj = json.loads(response.text)
        meta_obj["timestamp"] = convert_str_to_datetime(meta_obj["timestamp"])
        print("Response content:", meta_obj)
        return meta_obj
    else:
        print("GET request failed with status code:", response.status_code)


def return_latest_otp_later_than(given_timestamp, max_attempts=3, wait_time=5):
    attempts = 0
    given_timestamp = truncate_microseconds(given_timestamp)

    while attempts < max_attempts:
        otp_meta = get_latest_otp_from_mail()
        otp = otp_meta["otp"]
        timestamp = truncate_microseconds(otp_meta["timestamp"])

        if timestamp >= given_timestamp:
            return otp

        attempts += 1
        if attempts < max_attempts:
            print(
                f"Latest OTP timestamp ({timestamp}) is not later than the given timestamp ({given_timestamp}). Retrying in {wait_time} seconds...")
            time.sleep(wait_time)

    return None


if __name__ == '__main__':
    otp_sent_timestamp = set_timezone_in_datetime(datetime.now())
    return_latest_otp_later_than(otp_sent_timestamp)