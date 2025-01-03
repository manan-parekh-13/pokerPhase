import logging
from datetime import datetime
from kiteconnect.utils import log_info_and_notify, get_product_type_from_ws_id
from kiteconnect.global_stuff import (get_kite_client_from_cache, get_instrument_token_map_from_cache,
                                      get_opportunity_queue)
import asyncio
from mysql_config import add


async def consume_opportunity():
    while True:
        try:
            queue = get_opportunity_queue()
            # logging.critical(f"Current queue length: {queue.qsize()}")
            if not queue.empty():
                opportunity = await queue.get()
                # logging.critical(
                #     "Opportunity created at {}, received at {}".format(opportunity.created_at, datetime.now()))
                asyncio.create_task(realise_and_save_arbitrage_opportunity(opportunity))
                queue.task_done()
            else:
                await asyncio.sleep(0.001)
        except Exception as e:
            logging.critical(f"Error in consume_opportunity: {e}", exc_info=True)


async def realise_and_save_arbitrage_opportunity(opportunity):

    opportunity.opp_received_in_queue_at = datetime.now()

    kite_client = get_kite_client_from_cache()
    product_type = get_product_type_from_ws_id(opportunity.ws_id)

    buy_order_task = asyncio.create_task(
        place_order_for_opportunity_by_transaction_type(opportunity,
                                                        kite_client.TRANSACTION_TYPE_BUY,
                                                        product_type))
    opportunity.opp_buy_task_created_at = datetime.now()
    # logging.critical("Opportunity created at {} buy task created at {}".format(opportunity.created_at, datetime.now()))

    sell_order_task = asyncio.create_task(
        place_order_for_opportunity_by_transaction_type(opportunity,
                                                        kite_client.TRANSACTION_TYPE_SELL,
                                                        product_type))
    opportunity.opp_sell_task_created_at = datetime.now()
    # logging.critical("Opportunity created at {} sell task created at {}".format(opportunity.created_at, datetime.now()))

    opportunity.buy_order_id = await buy_order_task
    opportunity.sell_order_id = await sell_order_task

    add(opportunity)


async def place_order_for_opportunity_by_transaction_type(opportunity, transaction_type, product_type):
    # logging.critical("Opportunity created at {} {} task received at {}"
    #               .format(opportunity.created_at, transaction_type, datetime.now()))
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
        order_id = await asyncio.to_thread(kite_client.place_order, **order_params)
        if transaction_type == kite_client.TRANSACTION_TYPE_BUY:
            opportunity.buy_ordered_at = datetime.now()
        else:
            opportunity.sell_ordered_at = datetime.now()
        # log_info_and_notify("Order placed for: {}, {} {} at price: {}"
        #                     .format(instrument['trading_symbol'], opportunity.quantity, transaction_type, price))
        # logging.critical("Order placed for: {}, {} {} at price: {}"
        #                     .format(instrument['trading_symbol'], opportunity.quantity, transaction_type, price))
        return order_id
    except Exception as e:
        log_info_and_notify("Error while ordering: {}".format(e))
        return None
