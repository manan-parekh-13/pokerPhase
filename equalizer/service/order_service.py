from kiteconnect.login import get_kite_client_from_cache
from equalizer.web import global_cache
from Models.arbitrage_opportunity import ArbitrageOpportunity
import logging
from kiteconnect.utils import send_slack_message

logging.basicConfig(level=logging.DEBUG)


def realise_arbitrage_opportunity(opportunity):
    if not opportunity:
        return None

    try:
        kite_client = get_kite_client_from_cache()

        # create first order for the older ticker
        if opportunity.buy_source_ticker_time >= opportunity.sell_source_ticker_time:
            buy_order_id = place_order_for_opportunity_by_transaction_type(opportunity,
                                                                           kite_client.TRANSACTION_TYPE_BUY)
            sell_order_id = place_order_for_opportunity_by_transaction_type(opportunity,
                                                                            kite_client.TRANSACTION_TYPE_SELL)
        else:
            sell_order_id = place_order_for_opportunity_by_transaction_type(opportunity,
                                                                            kite_client.TRANSACTION_TYPE_SELL)
            buy_order_id = place_order_for_opportunity_by_transaction_type(opportunity,
                                                                           kite_client.TRANSACTION_TYPE_BUY)

        opportunity.buy_order_id = buy_order_id
        opportunity.sell_order_id = sell_order_id
        opportunity.status = ArbitrageOpportunity.TRIED

    except Exception as e:
        send_slack_message("Error while ordering: {}".format(e))
        opportunity.status = ArbitrageOpportunity.FAILED

    return opportunity


def place_order_for_opportunity_by_transaction_type(opportunity, transaction_type):
    kite_client = get_kite_client_from_cache()
    instrument_token_map = global_cache['instrument_map']

    if transaction_type == kite_client.TRANSACTION_TYPE_BUY:
        instrument = instrument_token_map[opportunity.buy_source]
    else:
        instrument = instrument_token_map[opportunity.sell_source]
    return kite_client.place_order(
        variety=kite_client.VARIETY_REGULAR,
        product=kite_client.PRODUCT_CNC,
        order_type=kite_client.ORDER_TYPE_LIMIT,
        validity=kite_client.VALIDITY_IOC,
        exchange=instrument['exchange'],
        trading_symbol=instrument['trading_symbol'],
        transaction_type=transaction_type,
        quantity=opportunity.quantity,
        price=opportunity.sell_price
    )
