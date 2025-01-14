from datetime import datetime
from kiteconnect.global_stuff import get_latest_aggregate_data_from_global_cache
from Models.aggregate_data import init_aggregate_data_for_instrument_and_ws_id
from mysql_config import add_all


def save_aggregate_data_for_tickers(existing_aggregate_data, new_ticks):
    for instrument_token, latest_tick_for_instrument in new_ticks.items():
        if instrument_token in existing_aggregate_data:
            prev_ticker_for_instrument = existing_aggregate_data.get(instrument_token)
            existing_aggregate_data[instrument_token] = get_new_aggregate_data_from_pre_value(prev_ticker_for_instrument)
        else:
            existing_aggregate_data[instrument_token] = {
                'ticker_time': datetime.now().timestamp(),
                'started_at': datetime.now()
            }


def get_new_aggregate_data_from_pre_value(prev_ticker_for_instrument):
    current_time = datetime.now().timestamp()
    new_time_diff = current_time - prev_ticker_for_instrument['ticker_time']

    new_min = min(new_time_diff, prev_ticker_for_instrument['min']) if 'min' in prev_ticker_for_instrument else (
        new_time_diff)
    new_max = max(new_time_diff, prev_ticker_for_instrument['max']) if 'max' in prev_ticker_for_instrument else (
        new_time_diff)

    new_n = (prev_ticker_for_instrument.get('n') or 0) + 1
    new_sum_of_time_diff = (prev_ticker_for_instrument.get('sum_of_time_diff') or 0) + new_time_diff
    new_sum_of_square_of_time_diff = (prev_ticker_for_instrument.get(
                                          'sum_of_square_of_time_diff') or 0) + new_time_diff ** 2
    return {
        'started_at': prev_ticker_for_instrument['started_at'],
        'ticker_time': current_time,
        'min': new_min,
        'max': new_max,
        'n': new_n,
        'sum_of_time_diff': new_sum_of_time_diff,
        'sum_of_square_of_time_diff': new_sum_of_square_of_time_diff
    }


def save_latest_aggregate_data_from_cache():
    ws_id_to_instrument_to_aggregates_map = get_latest_aggregate_data_from_global_cache()
    for ws_id, instrument_to_aggregates_map in ws_id_to_instrument_to_aggregates_map.items():
        if not instrument_to_aggregates_map:
            continue
        aggregate_data_rows = []
        for instrument_token, aggregate_data in instrument_to_aggregates_map.items():
            aggregate = init_aggregate_data_for_instrument_and_ws_id(
                data=aggregate_data, instrument_token=instrument_token, ws_id=ws_id)
            if not aggregate:
                continue
            aggregate_data_rows.append(aggregate)
        add_all(aggregate_data_rows)