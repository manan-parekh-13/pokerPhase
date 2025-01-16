from Models.arbitrage_opportunity import init_arbitrage_opportunities_from_strat_res_and_tickers
from charges_service import get_threshold_spread_coef_for_reqd_profit


def check_arbitrage(ticker1, ticker2, threshold_spread_coef, min_profit_percent,
                    product_type_int, max_buy_quantity, ws_id):
    # strategy 1 - buy from ticker2 and sell in ticker1
    strat_1_result = get_price_and_quantity_for_arbitrage(
        bids_data=ticker1['depth']['buy'],
        offers_data=ticker2['depth']['sell'],
        threshold_spread_coef=threshold_spread_coef,
        max_buy_quantity=max_buy_quantity
    )

    if strat_1_result['quantity'] > 0 and strat_1_result['buy_price'] > 0:
        spread_coef_for_reqd_profit = get_threshold_spread_coef_for_reqd_profit(
            buy_value=strat_1_result['quantity'] * strat_1_result['buy_price'],
            profit_percent=min_profit_percent,
            product_type_int=product_type_int
        )

        spread_coef = (strat_1_result['sell_price'] / strat_1_result['buy_price']) - 1
        if spread_coef >= spread_coef_for_reqd_profit:
            return init_arbitrage_opportunities_from_strat_res_and_tickers(
                buy_ticker=ticker2,
                sell_ticker=ticker1,
                strat_result=strat_1_result,
                ws_id=ws_id
            )

    # strategy 2 - buy from ticker1 and sell in ticker2
    strat_2_result = get_price_and_quantity_for_arbitrage(
        bids_data=ticker2['depth']['buy'],
        offers_data=ticker1['depth']['sell'],
        threshold_spread_coef=threshold_spread_coef,
        max_buy_quantity=max_buy_quantity
    )

    if strat_2_result['quantity'] > 0 and strat_2_result['buy_price'] > 0:
        spread_coef_for_reqd_profit = get_threshold_spread_coef_for_reqd_profit(
            buy_value=strat_2_result['quantity'] * strat_2_result['buy_price'],
            profit_percent=min_profit_percent,
            product_type_int=product_type_int
        )

        spread_coef = (strat_2_result['sell_price'] / strat_2_result['buy_price']) - 1
        if spread_coef >= spread_coef_for_reqd_profit:
            return init_arbitrage_opportunities_from_strat_res_and_tickers(
                buy_ticker=ticker1,
                sell_ticker=ticker2,
                strat_result=strat_2_result,
                ws_id=ws_id
            )

    return None


cdef dict get_price_and_quantity_for_arbitrage(list bids_data, list offers_data,
                                                double threshold_spread_coef, double max_buy_quantity):
    cdef double quantity = 0
    cdef int current_offers_depth = 0
    cdef int current_bids_depth = 0
    cdef double buy_price, sell_price, spread_coef
    cdef double add_quantity

    while True:
        lowest_buy = offers_data[current_offers_depth]
        highest_sell = bids_data[current_bids_depth]

        buy_price = lowest_buy.price
        sell_price = highest_sell.price
        spread_coef = (sell_price - buy_price) / buy_price if buy_price > 0 else 0

        if spread_coef < threshold_spread_coef:
            break

        add_quantity = min(lowest_buy.left_quantity, highest_sell.left_quantity)
        quantity = min(quantity + add_quantity, max_buy_quantity)

        if quantity == max_buy_quantity or quantity == 0:
            break

        offers_data[current_offers_depth].left_quantity -= add_quantity
        if offers_data[current_offers_depth].left_quantity == 0:
            current_offers_depth += 1

        bids_data[current_bids_depth].left_quantity -= add_quantity
        if bids_data[current_bids_depth].left_quantity == 0:
            current_bids_depth += 1

        if current_offers_depth == 5 or current_bids_depth == 5:
            break

    return {'buy_price': buy_price, 'sell_price': sell_price, 'quantity': quantity}


