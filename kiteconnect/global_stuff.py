import logging
from datetime import datetime, timedelta
from kiteconnect.utils import get_env_variable, log_info_and_notify
from kiteconnect import KiteConnect
from flask import abort
from asyncio import Queue
import asyncio
import threading
from mysql_config import add
from kiteconnect.exceptions import OrderException

global_cache = {}
opportunity_queue = Queue(maxsize=4)
event_loop = None
lock = threading.Lock()


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


def get_latest_tick_by_instrument_token_from_global_cache(instrument_token):
    return global_cache['latest_tick_data'].get(instrument_token)


def update_latest_ticks_for_instrument_tokens_in_bulk(token_to_tick_map):
    with lock:
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


def add_buy_and_sell_task_to_queue(event):
    kite_client = get_kite_client_from_cache()
    try:
        if opportunity_queue.qsize() < opportunity_queue.maxsize:
            kite_client.remove_margin_or_throw_error(event["reqd_margin"])
            logging.info(f"Removed margin: {event['reqd_margin']:.2f} for opportunity of {event['trading_symbol']}")
            asyncio.run_coroutine_threadsafe(opportunity_queue.put(event), event_loop)
        else:
            event["opportunity"].order_on_hold = True
            logging.info(f"Didn't remove any margin for opportunity of {event['trading_symbol']} due to full queue")
            add(event["opportunity"])
    except OrderException:
        event["opportunity"].low_margin_hold = True
        logging.info(f"Didn't remove any margin for opportunity of {event['trading_symbol']} due to low margin")
        add(event["opportunity"])
    except Exception as e:
        kite_client.add_margin(event["reqd_margin"])
        logging.info(f"Added margin: {event['reqd_margin']:.2f} for opportunity of {event['trading_symbol']} "
                     f"upon exception while adding task to queue")
        log_info_and_notify("Error while adding task to queue: {}".format(e))


def get_opportunity_queue():
    return opportunity_queue


def set_event_loop(value):
    global event_loop
    event_loop = value


def get_product_int_for_product_type(product_type):
    kite_client = get_kite_client_from_cache()
    if product_type == kite_client.PRODUCT_MIS:
        return kite_client.PRODUCT_MIS_INT
    if product_type == kite_client.PRODUCT_CNC:
        return kite_client.PRODUCT_CNC_INT
    if product_type == kite_client.PRODUCT_NRML:
        return kite_client.PRODUCT_NRML_INT
    if product_type == kite_client.PRODUCT_CO:
        return kite_client.PRODUCT_CO_INT
