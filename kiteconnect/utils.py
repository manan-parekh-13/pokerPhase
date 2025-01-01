import os
from datetime import datetime
import pytz
import requests
import json
import logging

AWS_WEBHOOK_URL = 'https://hooks.slack.com/services/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'
LOCAL_WEBHOOK_URL = 'https://hooks.slack.com/services/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'


def get_env_variable(parameter_name):
    return os.getenv(parameter_name)


def convert_str_to_datetime(timestamp_str):
    # Convert string to datetime object
    timestamp_utc = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S.%fZ")

    # Set UTC timezone
    utc_timezone = pytz.timezone('UTC')
    timestamp_utc = utc_timezone.localize(timestamp_utc)

    # Convert to IST timezone
    ist_timezone = pytz.timezone('Asia/Kolkata')
    timestamp_ist = timestamp_utc.astimezone(ist_timezone)

    return timestamp_ist


def datetime_to_str(dt: datetime):
    return dt.strftime("%d/%m/%Y %H:%M:%S")


def dict_to_string(obj: dict) -> str:
    """
    Converts a dictionary or object into a formatted string with each key-value pair on a new line.

    :param obj: The dictionary or object to format
    :return: A string with each key-value pair in the format 'key: value', one per line
    """
    if not isinstance(obj, dict):
        raise ValueError("Input must be a dictionary.")

    return '\n'.join(f"{key}: {value}" for key, value in obj.items())


def set_timezone_in_datetime(timestamp, time_zone='Asia/Kolkata'):
    timezone = pytz.timezone(time_zone)
    return timestamp.astimezone(timezone)


def truncate_microseconds(timestamp):
    return timestamp.replace(microsecond=0)


def log_info_and_notify(message):
    logging.info(json.dumps(message))
    send_slack_message(message)


def log_error_and_notify(message):
    logging.error(json.dumps(message))
    send_slack_message(message)


def send_slack_message(message):
    webhook_url = get_env_variable('SLACK_UPDATE_CHANNEL_WEBHOOK')
    data = {'text': message}
    headers = {'Content-Type': 'application/json'}
    response = requests.post(webhook_url, data=json.dumps(data), headers=headers)
    if response.status_code != 200:
        logging.error(f"Failed to send Slack message: {response.text}")


def get_product_type_from_ws_id(ws_id):
    return ws_id.split('_')[0]


def convert_to_micro(value):
    """Convert a datetime object to a Unix timestamp with microsecond accuracy."""
    if value is not None:
        microseconds = value.microsecond  # Extract microseconds
        return int((value.timestamp() * 1e6) + microseconds)  # Convert seconds to microseconds and add microseconds
    return None


def get_time_diff_in_micro(start_time):
    end_time_in_micro = convert_to_micro(datetime.now())
    start_time_in_micro = convert_to_micro(start_time)
    return end_time_in_micro - start_time_in_micro
