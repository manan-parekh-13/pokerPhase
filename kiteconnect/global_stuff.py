from kiteconnect.utils import get_env_variable
from kiteconnect import KiteConnect
from flask import abort
import threading
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import Value, Lock
import kiteconnect.exceptions as ex

global_cache = {}
shared_avl_margin = 0.0
avl_order_tasks = 0
lock = threading.Lock()
process_lock = Lock()


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


def init_process_pool_executors():
    executor_0 = ProcessPoolExecutor(max_workers=1)
    executor_1 = ProcessPoolExecutor(max_workers=1)
    executors = {
        0: executor_0,
        1: executor_1
    }
    global_cache['executors'] = executors


def get_executor_by_process_id(process_id):
    return global_cache['executors'][process_id]


def init_avl_margin(avl_margin):
    global shared_avl_margin
    shared_avl_margin = Value("d", avl_margin)


def add_margin(delta_margin):
    with process_lock:
        global shared_avl_margin
        shared_avl_margin.value += delta_margin
        return shared_avl_margin.value


def get_available_margin():
    with process_lock:
        global shared_avl_margin
        return shared_avl_margin.value or 0.0


def set_available_margin(new_margin):
    with process_lock:
        global shared_avl_margin
        shared_avl_margin.value = new_margin


def remove_margin_or_throw_error(reqd_margin):
    with process_lock:
        global shared_avl_margin
        if shared_avl_margin.value < reqd_margin:
            raise ex.OrderException(
                "Avl margin {avl_margin} lower than reqd margin: {reqd_margin}".format(
                    avl_margin=shared_avl_margin.value, reqd_margin=reqd_margin)
            )
        shared_avl_margin.value -= reqd_margin


def init_avl_order_tasks(num_of_tasks):
    global avl_order_tasks
    avl_order_tasks = Value("i", num_of_tasks)


def remove_order_task_if_avl():
    with process_lock:
        global avl_order_tasks
        if avl_order_tasks.value > 0:
            avl_order_tasks.value -= 1
            return True
        else:
            return False


def add_to_avl_order_task():
    with process_lock:
        global avl_order_tasks
        avl_order_tasks.value += 1


def is_opportunity_stale(opportunity):
    latest_tick_for_buy_source = get_latest_tick_by_instrument_token_from_global_cache(opportunity.buy_source)
    if latest_tick_for_buy_source['ticker_received_time'] > opportunity.buy_source_ticker_time:
        return True

    latest_tick_for_sell_source = get_latest_tick_by_instrument_token_from_global_cache(opportunity.sell_source)
    if latest_tick_for_sell_source['ticker_received_time'] > opportunity.sell_source_ticker_time:
        return True

    return False
