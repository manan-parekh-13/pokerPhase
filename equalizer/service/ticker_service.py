from datetime import datetime

from Models.tickerData import TickerData
from Models.depthData import DepthData
from mysql_config import add_all


def save_ticker_data(ticks):
    if not ticks:
        return
    processed_ticks = list(map(lambda x: process_tick(x), ticks))
    add_all(processed_ticks)


def process_tick(tick):
    if not tick:
        return None

    tick["ticker_received_time"] = datetime.now()

    if 'ohlc' in tick:
        tick.update(tick.pop('ohlc'))

    if 'depth' in tick:
        flat_depths = flatten_depth(tick['depth'], tick['exchange_timestamp'], tick['instrument_token'])
        tick.pop('depth', None)
        add_all(flat_depths)

    return TickerData(**tick)


def flatten_depth(depth, exchange_timestamp, instrument_token):
    flat_depth_list = []
    for key in depth:
        for item in depth[key]:
            item['type'] = key  # Add 'type' field to indicate buy/sell
            item['exchange_timestamp'] = exchange_timestamp
            item['instrument_token'] = instrument_token
            flat_depth_list.append(DepthData(**item))
    return flat_depth_list


