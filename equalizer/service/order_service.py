from datetime import datetime
from kiteconnect.utils import log_info_and_notify, get_product_type_from_ws_id
from kiteconnect.global_stuff import (get_kite_client_from_cache, get_instrument_token_map_from_cache,
                                      get_opportunity_queue)
import asyncio
from mysql_config import add


async def consume_opportunity():
    while True:
        queue = get_opportunity_queue()
        if not queue.empty():
            opportunity = queue.get()
            await realise_and_save_arbitrage_opportunity(opportunity)
        await asyncio.sleep(0.0001)


async def realise_and_save_arbitrage_opportunity(opportunity):
    kite_client = get_kite_client_from_cache()
    product_type = get_product_type_from_ws_id(opportunity.ws_id)

    buy_order_task = asyncio.create_task(
        place_order_for_opportunity_by_transaction_type(opportunity,
                                                        kite_client.TRANSACTION_TYPE_BUY,
                                                        product_type))
    sell_order_task = asyncio.create_task(
        place_order_for_opportunity_by_transaction_type(opportunity,
                                                        kite_client.TRANSACTION_TYPE_SELL,
                                                        product_type))

    opportunity.buy_order_id = await buy_order_task
    opportunity.sell_order_id = await sell_order_task

    opportunity.buy_ordered_at = datetime.now() if opportunity.buy_order_id else None
    opportunity.sell_ordered_at = datetime.now() if opportunity.sell_order_id else None

    add(opportunity)


def place_order_for_opportunity_by_transaction_type(opportunity, transaction_type, product_type):
    kite_client = get_kite_client_from_cache()
    instrument_token_map = get_instrument_token_map_from_cache()

    if transaction_type == kite_client.TRANSACTION_TYPE_BUY:
        instrument = instrument_token_map.get(opportunity.buy_source)
        price = opportunity.buy_price
    else:
        instrument = instrument_token_map.get(opportunity.sell_source)
        price = opportunity.sell_price
    try:
        order_id = kite_client.place_order(
            variety=kite_client.VARIETY_REGULAR,
            product=product_type,
            order_type=kite_client.ORDER_TYPE_LIMIT,
            validity=kite_client.VALIDITY_IOC,
            exchange=instrument['exchange'],
            tradingsymbol=instrument['trading_symbol'],
            transaction_type=transaction_type,
            quantity=int(opportunity.quantity),
            price=price
        )
        log_info_and_notify("Order placed for: {}, {} {} at price: {}"
                            .format(instrument['trading_symbol'], opportunity.quantity, transaction_type, price))
        return order_id
    except Exception as e:
        log_info_and_notify("Error while ordering: {}".format(e))
        return None
