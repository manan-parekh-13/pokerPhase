import logging
from datetime import datetime

from equalizer.service.ticker_service import is_opportunity_stale
from kiteconnect.utils import log_info_and_notify
from kiteconnect.global_stuff import (get_kite_client_from_cache, get_instrument_token_map_from_cache,
                                      get_opportunity_queue)
import asyncio
from mysql_config import add_all, add
from Models.order_info import OrderInfo, init_order_info


async def consume_buy_or_sell_tasks(consumer_id):
    while True:
        try:
            queue = get_opportunity_queue()
            if not queue.empty():
                task = queue.get()
                place_order(task["opportunity"], task["transaction_type"], task["product_type"])
                queue.task_done()
                logging.debug("Completed {} task for opportunity {} using consumer {}."
                              .format(task["transaction_type"], task["opportunity"].id, consumer_id))
            else:
                await asyncio.sleep(0.001)
        except Exception as e:
            logging.critical(f"Error in consume_buy_or_sell_tasks: {e}", exc_info=True)


def place_order(opportunity, transaction_type, product_type):
    kite_client = get_kite_client_from_cache()

    if transaction_type == kite_client.TRANSACTION_TYPE_BUY:
        opportunity.opp_buy_task_received_at = datetime.now()
    else:
        opportunity.opp_sell_task_received_at = datetime.now()

    instrument_token_map = get_instrument_token_map_from_cache()

    if transaction_type == kite_client.TRANSACTION_TYPE_BUY:
        instrument = instrument_token_map.get(opportunity.buy_source)
        price = opportunity.buy_price
    else:
        instrument = instrument_token_map.get(opportunity.sell_source)
        price = opportunity.sell_price

    order_params = {
        "variety": kite_client.VARIETY_REGULAR,
        "product": product_type,
        "order_type": kite_client.ORDER_TYPE_MARKET,
        "validity": kite_client.VALIDITY_IOC,
        "exchange": instrument['exchange'],
        "tradingsymbol": instrument['trading_symbol'],
        "transaction_type": transaction_type,
        "quantity": int(opportunity.quantity),
        # "price": price
    }

    opportunity.is_stale = is_opportunity_stale(opportunity) if not opportunity.is_stale else opportunity.is_stale

    if opportunity.is_stale:
        return None

    try:
        order_id = kite_client.place_order(**order_params)
        if transaction_type == kite_client.TRANSACTION_TYPE_BUY:
            opportunity.buy_ordered_at = datetime.now()
            opportunity.buy_order_id = order_id
        else:
            opportunity.sell_ordered_at = datetime.now()
            opportunity.sell_order_id = order_id

        if not opportunity.buy_order_id or not opportunity.sell_order_id:
            return

        add(opportunity)
    except Exception as e:
        log_info_and_notify("Error while ordering: {}".format(e))
        return None


def save_order_info(order_list):
    """
    Parse an order_list, check if rows with the same order_id exist in the database,
    and saves orders that do not exist.

    :param order_list: List of order dictionaries to check
    """
    orders_to_be_saved = []

    for order_data in order_list:
        order_id = order_data['order_id']
        existing_order = OrderInfo.get_order_by_id(order_id)

        if existing_order:
            continue
        else:
            orders_to_be_saved.append(init_order_info(order_data))

    add_all(orders_to_be_saved)

