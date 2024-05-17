from datetime import datetime, timedelta
from kiteconnect.login import set_timezone_in_datetime


# Function to check if the ticker is valid
def is_ticker_valid(ticker):
    if not ticker:
        return False

    if not ticker['tradable']:
        return False

    time_difference = set_timezone_in_datetime(datetime.now()) - set_timezone_in_datetime(ticker['exchange_timestamp'])
    allowed_time_difference = timedelta(seconds=2)
    if time_difference > allowed_time_difference:
        return False

    mode = ticker['mode']
    if mode == 'full':
        return 'depth' in ticker.keys()
    if mode == 'quote':
        return 'ohlc' in ticker.keys()
    return False

