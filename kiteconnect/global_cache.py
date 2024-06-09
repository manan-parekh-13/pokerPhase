from datetime import datetime, timedelta
from kiteconnect.utils import get_env_variable
from kiteconnect import KiteConnect
from flask import abort

global_cache = {}


def get_kite_client(root=None, debug=False):
    """Returns a kite client object
    """
    user_id = get_env_variable('USER_ID')
    if not user_id:
        abort(500, "Invalid user_id.")

    password = get_env_variable('PASSWORD')
    if not password:
        abort(500, "Invalid password.")

    return KiteConnect(debug=debug, root=root, user_id=user_id, password=password)


def get_kite_client_from_cache():
    if "kite_client" in global_cache:
        return global_cache.get("kite_client")
    kite = get_kite_client()
    global_cache['kite_client'] = kite
    return kite


def get_latest_aggregate_data_for_ws_id_from_global_cache(ws_id):
    return global_cache['aggregate_data'][ws_id] if ws_id in global_cache['aggregate_data'] else None


def get_latest_aggregate_data_from_global_cache():
    return global_cache['aggregate_data']


def init_latest_tick_data_in_global_cache():
    global_cache['latest_tick_data'] = {}


def init_aggregate_data_for_ws_in_global_cache(ws_id):
    if 'aggregate_data' not in global_cache:
        global_cache['aggregate_data'] = {}
    global_cache['aggregate_data'][ws_id] = {}


def init_instrument_token_to_equivalent_token_map(map):
    global_cache['token_to_equivalent_map'] = map


def get_latest_tick_by_instrument_token_from_global_cache(instrument_token):
    return global_cache['latest_tick_data'].get(instrument_token)


def update_latest_ticks_for_instrument_tokens_in_bulk(token_to_tick_map):
    global_cache['latest_tick_data'].update(token_to_tick_map)


def setup_order_hold_for_time_in_seconds(time_in_s):
    global_cache['order_on_hold_till'] = datetime.now() + timedelta(seconds=time_in_s)


def is_order_on_hold_currently():
    if 'order_on_hold_till' in global_cache:
        if global_cache['order_on_hold_till'] >= datetime.now():
            return True
        else:
            del (global_cache['order_on_hold_till'])
    return False


def get_instrument_token_map_from_cache():
    return global_cache['token_to_equivalent_map']