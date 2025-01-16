from datetime import datetime
from typing import Dict, Union

def get_new_aggregate_data_from_pre_value(
    prev_ticker_for_instrument: Dict[str, Union[float, int, str]]
) -> Dict[str, Union[float, int, str]]:
    cdef float current_time = datetime.now().timestamp()
    cdef float new_time_diff = current_time - prev_ticker_for_instrument['ticker_time']

    cdef float new_min
    if 'min' in prev_ticker_for_instrument:
        new_min = min(new_time_diff, prev_ticker_for_instrument['min'])
    else:
        new_min = new_time_diff

    cdef float new_max
    if 'max' in prev_ticker_for_instrument:
        new_max = max(new_time_diff, prev_ticker_for_instrument['max'])
    else:
        new_max = new_time_diff

    cdef int new_n = (prev_ticker_for_instrument.get('n') or 0) + 1
    cdef float new_sum_of_time_diff = (prev_ticker_for_instrument.get('sum_of_time_diff') or 0) + new_time_diff
    cdef float new_sum_of_square_of_time_diff = (prev_ticker_for_instrument.get('sum_of_square_of_time_diff') or 0) + new_time_diff ** 2

    return {
        'started_at': prev_ticker_for_instrument['started_at'],
        'ticker_time': current_time,
        'min': new_min,
        'max': new_max,
        'n': new_n,
        'sum_of_time_diff': new_sum_of_time_diff,
        'sum_of_square_of_time_diff': new_sum_of_square_of_time_diff
    }

