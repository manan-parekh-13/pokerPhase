import os
from datetime import datetime
import pytz
import requests
import json
import logging

logging.basicConfig(level=logging.DEBUG)

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


def set_timezone_in_datetime(timestamp, time_zone='Asia/Kolkata'):
    timezone = pytz.timezone(time_zone)
    return timestamp.astimezone(timezone)


def truncate_microseconds(timestamp):
    return timestamp.replace(microsecond=0)


def log_and_notify(message):
    logging.info(json.dumps(message))

    webhook_url = get_env_variable('SLACK_UPDATE_CHANNEL_WEBHOOK')

    data = {'text': message}
    headers = {'Content-Type': 'application/json'}
    response = requests.post(webhook_url, data=json.dumps(data), headers=headers)
    if response.status_code != 200:
        logging.error(f"Failed to send Slack message: {response.text}")
