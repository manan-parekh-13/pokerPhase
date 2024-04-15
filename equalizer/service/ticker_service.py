from datetime import datetime

from Models.tickerData import TickerData
from Models.depthData import DepthData
from mysql_config import add_all, add


def save_ticker_data(ticks):
    if not ticks:
        return
    for tick in ticks:
        processed_tick_and_depth = process_tick(tick)
        processed_tick = processed_tick_and_depth[0]
        saved_tick = add(processed_tick)

        processed_depths = processed_tick_and_depth[1]
        for depth in processed_depths:
            depth.ticker_id = saved_tick.id

        add_all(processed_depths)


def process_tick(tick):
    if not tick:
        return None

    tick["ticker_received_time"] = datetime.now()

    if 'ohlc' in tick:
        tick.update(tick.pop('ohlc'))

    if 'depth' in tick:
        flat_depths = flatten_depth(tick['depth'], tick['exchange_timestamp'], tick['instrument_token'])
        tick.pop('depth', None)

    return TickerData(**tick), flat_depths


def flatten_depth(depth, exchange_timestamp, instrument_token):
    flat_depth_list = []
    for key in depth:
        for item in depth[key]:
            item['type'] = key  # Add 'type' field to indicate buy/sell
            item['exchange_timestamp'] = exchange_timestamp
            item['instrument_token'] = instrument_token
            flat_depth_list.append(DepthData(**item))
    return flat_depth_list


# Function to check if the ticker is valid
def is_ticker_valid(ticker):
    mode = ticker['mode']
    if mode == 'full':
        return 'depth' in ticker.keys()
    if mode == 'quote':
        return 'ohlc' in ticker.keys()
    return False


def are_tickers_valid(ticks):
    all_ticks_valid = True
    for tick in ticks:
        valid = is_ticker_valid(tick)
        if not valid:
            all_ticks_valid = False
    return all_ticks_valid

