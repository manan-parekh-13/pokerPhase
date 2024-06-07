import logging
from datetime import datetime
from kiteconnect.utils import log_and_notify
from kiteconnect.global_cache import (setup_order_hold_for_time_in_seconds, get_kite_client_from_cache,
                                      get_instrument_token_map_from_cache)

logging.basicConfig(level=logging.DEBUG)


def realise_arbitrage_opportunity(opportunity, product_type):
    kite_client = get_kite_client_from_cache()

    opportunity.buy_order_id = place_order_for_opportunity_by_transaction_type(
        opportunity, kite_client.TRANSACTION_TYPE_BUY, product_type)

    if not opportunity.buy_order_id:
        return

    setup_order_hold_for_time_in_seconds(60)
    opportunity.buy_ordered_at = datetime.now()
    opportunity.sell_order_id = place_order_for_opportunity_by_transaction_type(
        opportunity, kite_client.TRANSACTION_TYPE_SELL, product_type)
    opportunity.sell_ordered_at = datetime.now() if opportunity.sell_order_id else None

    return opportunity


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
            quantity=opportunity.quantity,
            price=price
        )
        log_and_notify("Order placed for: {}, {} {} at price: {}"
                       .format(instrument['trading_symbol'], opportunity.quantity, transaction_type, price))
        return order_id
    except Exception as e:
        log_and_notify("Error while ordering: {}".format(e))
        return None
