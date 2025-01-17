import logging
import threading
from datetime import datetime

from equalizer.service.ticker_service import is_opportunity_stale
from kiteconnect.utils import log_info_and_notify, get_env_variable
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
                task = await queue.get()
                kite_client = get_kite_client_from_cache()
                opportunity = task["opportunity"]

                opportunity.is_stale = is_opportunity_stale(
                    opportunity) if not opportunity.is_stale else opportunity.is_stale

                if not opportunity.is_stale:
                    buy_task = asyncio.create_task(
                        place_order(opportunity, kite_client.TRANSACTION_TYPE_BUY, task["product_type"],
                                    task["leverage"])
                    )
                    sell_task = asyncio.create_task(
                        place_order(opportunity, kite_client.TRANSACTION_TYPE_SELL, task["product_type"],
                                    task["leverage"])
                    )
                    await buy_task
                    await sell_task
                else:
                    kite_client.add_margin(task["reqd_margin"])

                add(opportunity)

                queue.task_done()
                logging.info("Realised opportunity {} using consumer {} on process_thread {}."
                             .format(task["opportunity"].id, consumer_id, threading.current_thread().name))
            else:
                await asyncio.sleep(0.001)
        except Exception as e:
            logging.critical(f"Error in consume_buy_or_sell_tasks: {e}", exc_info=True)


async def place_order(opportunity, transaction_type, product_type, leverage):
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

    try:
        is_order_allowed = get_env_variable("ALLOW_ORDER")
        if is_order_allowed != "yes":
            available_margin = kite_client.get_available_margin()
            new_margin = kite_client.add_margin(order_params["quantity"] * price / leverage)
            await asyncio.sleep(0.1)
            logging.info(
                "Previous margin {}, New margin: {} for {} order of {}_{} at price {} and quantity {} for "
                "opportunity: {}"
                .format(available_margin, new_margin, transaction_type,
                        order_params["exchange"], order_params["tradingsymbol"],
                        price, order_params["quantity"], opportunity.id
                        )
            )
            order_id = 10 ** 15 + datetime.now().timestamp()
        else:
            order_id = kite_client.place_order(**order_params)

        if transaction_type == kite_client.TRANSACTION_TYPE_BUY:
            opportunity.buy_ordered_at = datetime.now()
            opportunity.buy_order_id = order_id
        else:
            opportunity.sell_ordered_at = datetime.now()
            opportunity.sell_order_id = order_id
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
