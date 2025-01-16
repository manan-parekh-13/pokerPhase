def calc_transac_charges(double order_value, int product_type, int transaction_type):
    if product_type == 1:  # kite_client.PRODUCT_CNC
        if transaction_type == 1:  # kite_client.TRANSACTION_TYPE_BUY
            return 0.001196 * order_value
        else:
            return 15.93 + 0.001046 * order_value
    elif product_type == 2 and order_value > 66000.0:  # kite_client.PRODUCT_MIS
        if transaction_type == 1:  # kite_client.TRANSACTION_TYPE_BUY
            return 23.6 + 0.000076 * order_value
        else:
            return 23.6 + 0.000296 * order_value
    elif product_type == 2 and order_value <= 66000.0:  # kite_client.PRODUCT_MIS
        if transaction_type == 1:  # kite_client.TRANSACTION_TYPE_BUY
            return 0.00043 * order_value
        else:
            return 0.00065 * order_value
    return 0.0


def get_threshold_spread_coef_for_reqd_profit(double buy_value, double profit_percent, int product_type_int):
    cdef double profit_coef = profit_percent / 100.0

    if product_type_int == 2: # PRODUCT_CNC_INT
        return ((15.93 + 0.002241 * buy_value) * (1 + profit_coef)) / buy_value + profit_coef
    elif product_type_int == 1 and buy_value > 66000.0: # PRODUCT_MIS_INT
        return ((47.2 + 0.00038 * buy_value) * (1 + profit_coef)) / buy_value + profit_coef
    elif product_type_int == 1 and buy_value <= 66000.0: # PRODUCT_MIS_INT
        return ((0.0011 * buy_value) * (1 + profit_coef)) / buy_value + profit_coef
    return 0.0
