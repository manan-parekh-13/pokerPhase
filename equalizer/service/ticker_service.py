from datetime import datetime, timedelta
from kiteconnect.login import set_timezone_in_datetime
from kiteconnect.global_cache import get_latest_tick_by_instrument_token_from_global_cache


# Function to check if the ticker is valid
def is_ticker_valid(ticker):
    if not ticker:
        return False

    if not ticker['tradable']:
        return False

    if not ticker['last_price']:
        return False

    if not ticker['depth']:
        return False

    time_difference = set_timezone_in_datetime(datetime.now()) - set_timezone_in_datetime(ticker['exchange_timestamp'])
    allowed_time_difference = timedelta(seconds=2)
    # todo @manan - condition can be removed once we get data for every instrument_token
    # if time_difference > allowed_time_difference:
    #     return False

    mode = ticker['mode']
    if mode == 'full':
        return 'depth' in ticker.keys()
    if mode == 'quote':
        return 'ohlc' in ticker.keys()
    return False


def reduce_quantity_from_topmost_depth(depth, quantity):
    depth[0]['quantity'] = depth[0]['quantity'] - quantity
    if depth[0]['quantity'] == 0:
        depth.pop(0)


def is_ticker_stale(ticker):
    latest_ticker_for_instrument = get_latest_tick_by_instrument_token_from_global_cache(ticker['instrument_token'])
    return latest_ticker_for_instrument['ticker_received_time'] > ticker['ticker_received_time']
