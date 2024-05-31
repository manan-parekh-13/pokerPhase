from kiteconnect.login import get_kite_client_from_cache, global_cache
from Models.arbitrage_opportunity import ArbitrageOpportunity
import logging
from kiteconnect.utils import send_slack_message

logging.basicConfig(level=logging.DEBUG)


def realise_arbitrage_opportunity(opportunity, product_type):
    kite_client = get_kite_client_from_cache()

    # create first order for the older ticker
    if opportunity.buy_source_ticker_time >= opportunity.sell_source_ticker_time:
        buy_order_id = place_order_for_opportunity_by_transaction_type(opportunity,
                                                                       kite_client.TRANSACTION_TYPE_BUY,
                                                                       product_type)
        if buy_order_id:
            sell_order_id = place_order_for_opportunity_by_transaction_type(opportunity,
                                                                            kite_client.TRANSACTION_TYPE_SELL,
                                                                            product_type)
    else:
        sell_order_id = place_order_for_opportunity_by_transaction_type(opportunity,
                                                                        kite_client.TRANSACTION_TYPE_SELL,
                                                                        product_type)
        if sell_order_id:
            buy_order_id = place_order_for_opportunity_by_transaction_type(opportunity,
                                                                           kite_client.TRANSACTION_TYPE_BUY,
                                                                           product_type)

    opportunity.buy_order_id = buy_order_id
    opportunity.buy_status = kite_client.TRIED if buy_order_id else kite_client.FAILED
    opportunity.sell_order_id = sell_order_id
    opportunity.sell_status = kite_client.TRIED if buy_order_id else kite_client.FAILED

    return opportunity


def place_order_for_opportunity_by_transaction_type(opportunity, transaction_type, product_type):
    kite_client = get_kite_client_from_cache()
    instrument_token_map = global_cache['instrument_map']

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
        send_slack_message("Order alert for: {}, {} {} at price: {}"
                           .format(instrument['trading_symbol'], opportunity.quantity, transaction_type, price))
        return order_id
    except Exception as e:
        send_slack_message("Error while ordering: {}".format(e))
        return None

