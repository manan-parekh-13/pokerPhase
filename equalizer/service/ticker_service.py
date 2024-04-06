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


# Function to check if the ticker is not older than a certain time difference from the current time
def is_recent_ticker(ticker, max_time_diff_in_sec):
    current_time = datetime.now()
    ticker_time = ticker['exchange_timestamp']
    time_difference = current_time - ticker_time
    return time_difference.total_seconds() <= max_time_diff_in_sec


def are_all_tickers_recent(latest_ticks, max_time_diff_in_sec):
    ticks = list(latest_ticks.values())
    all_ticks_recent = True
    for tick in ticks:
        recent = is_recent_ticker(tick, max_time_diff_in_sec)
        if not recent:
            all_ticks_recent = False
    return all_ticks_recent

