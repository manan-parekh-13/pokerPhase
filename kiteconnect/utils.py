import os
import datetime
import pytz
import requests
import json


def get_sensitive_parameter(parameter_name):
    if os.getenv(parameter_name):
        return os.getenv(parameter_name)
    # Use Google Cloud Secret Manager for GCP deployment
    else:
        # Fetch parameter from Secret Manager
        return None


def convert_str_to_datetime(timestamp_str):
    # Convert string to datetime object
    timestamp_utc = datetime.datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S.%fZ")

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


def send_slack_message(message):
    if get_sensitive_parameter('FLASK_ENV') == 'local':
        return

    webhook_url = 'https://hooks.slack.com/services/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'
    data = {'text': message}
    headers = {'Content-Type': 'application/json'}
    response = requests.post(webhook_url, data=json.dumps(data), headers=headers)
    if response.status_code != 200:
        print(f"Failed to send Slack message: {response.text}")