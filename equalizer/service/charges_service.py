from kiteconnect.global_cache import get_kite_client_from_cache
from decimal import Decimal


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


def get_threshold_spread_coef_for_reqd_profit(buy_value, profit_percent, product_type):
    kite_client = get_kite_client_from_cache()
    profit_coef = Decimal(profit_percent) / 100
    buy_value = Decimal(buy_value)
    if product_type == kite_client.PRODUCT_CNC:
        return ((Decimal(15.93) + Decimal(0.002241) * buy_value) * (Decimal(1) + profit_coef)) / buy_value + profit_coef
    if product_type == kite_client.PRODUCT_MIS and buy_value > 66000.0:
        return ((Decimal(47.2) + Decimal(0.00038) * buy_value) * (Decimal(1) + profit_coef)) / buy_value + profit_coef
    if product_type == kite_client.PRODUCT_MIS and buy_value <= 66000.0:
        return ((Decimal(0.0011) * buy_value) * (Decimal(1) + profit_coef)) / buy_value + profit_coef
