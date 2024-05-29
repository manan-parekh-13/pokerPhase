from kiteconnect.login import get_kite_client_from_cache


def calc_transac_charges(order_value, product_type, transaction_type):
    kite_client = get_kite_client_from_cache()
    if product_type == kite_client.PRODUCT_CNC:
        if transaction_type == kite_client.TRANSACTION_TYPE_BUY:
            return 0.001196 * order_value
        else:
            return 15.93 + 0.001046 * order_value
    if product_type == kite_client.PRODUCT_MIS and order_value > 66000.0:
        if transaction_type == kite_client.TRANSACTION_TYPE_BUY:
            return 23.6 + 0.000076 * order_value
        else:
            return 23.6 + 0.000296 * order_value
    if product_type == kite_client.PRODUCT_MIS and order_value <= 66000.0:
        if transaction_type == kite_client.TRANSACTION_TYPE_BUY:
            return 0.00043 * order_value
        else:
            return 0.00065 * order_value


def get_min_percentage_reqd_for_min_profit(max_buy_value, min_profit_coef, product_type):
    kite_client = get_kite_client_from_cache()
    if product_type == kite_client.PRODUCT_CNC:
        return ((15.93 + 0.002241*max_buy_value) * (1 + min_profit_coef))/max_buy_value + min_profit_coef
    if product_type == kite_client.PRODUCT_MIS and max_buy_value > 66000.0:
        return ((47.2 + 0.00038*max_buy_value) * (1 + min_profit_coef))/max_buy_value + min_profit_coef
    if product_type == kite_client.PRODUCT_MIS and max_buy_value <= 66000.0:
        return ((0 + 0.0011*max_buy_value) * (1 + min_profit_coef))/max_buy_value + min_profit_coef
