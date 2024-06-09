from Models.arbitrage_opportunity import init_arbitrage_opportunities_from_strat_res_and_tickers
from mysql_config import add_all
from equalizer.service.charges_service import get_threshold_spread_coef_for_reqd_profit
from equalizer.service.ticker_service import reduce_quantity_from_topmost_depth
from copy import deepcopy


def check_arbitrage(ticker1, ticker2, threshold_spread_coef, min_profit_percent, product_type, max_buy_quantity, ws_id):
    # strategy 1 - buy from ticker2 and sell in ticker1
    ticker1_bids = deepcopy(ticker1)['depth']['buy']
    ticker2_offers = deepcopy(ticker2)['depth']['sell']

    strat_1_result = get_price_and_quantity_for_arbitrage(bids_data=ticker1_bids,
                                                          offers_data=ticker2_offers,
                                                          threshold_spread_coef=threshold_spread_coef,
                                                          max_buy_quantity=max_buy_quantity)

    if strat_1_result['quantity'] > 0:
        spread_coef_for_reqd_profit = get_threshold_spread_coef_for_reqd_profit(
            buy_value=strat_1_result['quantity'] * strat_1_result['buy_price'],
            profit_percent=min_profit_percent,
            product_type=product_type)

        spread_coef = (strat_1_result['sell_price'] / strat_1_result['buy_price']) - 1
        if spread_coef >= spread_coef_for_reqd_profit:
            # In case strategy 1 has opportunities, strategy 2 can't have opportunities
            return init_arbitrage_opportunities_from_strat_res_and_tickers(buy_ticker=ticker2,
                                                                           sell_ticker=ticker1,
                                                                           strat_result=strat_1_result,
                                                                           ws_id=ws_id)

    # strategy 2 - buy from ticker1 and sell in ticker2
    ticker2_bids = deepcopy(ticker2)['depth']['buy']
    ticker1_offers = deepcopy(ticker1)['depth']['sell']
    strat_2_result = get_price_and_quantity_for_arbitrage(bids_data=ticker2_bids,
                                                          offers_data=ticker1_offers,
                                                          threshold_spread_coef=threshold_spread_coef,
                                                          max_buy_quantity=max_buy_quantity)

    if strat_2_result['quantity'] > 0:
        spread_coef_for_reqd_profit = get_threshold_spread_coef_for_reqd_profit(
            buy_value=strat_2_result['quantity'] * strat_2_result['buy_price'],
            profit_percent=min_profit_percent,
            product_type=product_type)

        spread_coef = (strat_2_result['sell_price'] / strat_2_result['buy_price']) - 1
        if spread_coef >= spread_coef_for_reqd_profit:
            return init_arbitrage_opportunities_from_strat_res_and_tickers(buy_ticker=ticker1,
                                                                           sell_ticker=ticker2,
                                                                           strat_result=strat_2_result,
                                                                           ws_id=ws_id)

    return None


def get_price_and_quantity_for_arbitrage(bids_data, offers_data, threshold_spread_coef, max_buy_quantity):
    quantity = 0

    while True:
        lowest_buy = offers_data[0]
        highest_sell = bids_data[0]

        buy_price = lowest_buy['price']
        sell_price = highest_sell['price']
        spread_coef = (sell_price - buy_price) / buy_price if buy_price > 0 else 0

        if spread_coef < threshold_spread_coef:
            break

        add_quantity = min(lowest_buy['quantity'], highest_sell['quantity'])
        quantity = min(quantity + add_quantity, max_buy_quantity)
        # quantity == 0 is only possible when zerodha sends us a stupid depth value
        if quantity == max_buy_quantity or quantity == 0:
            break;

        reduce_quantity_from_topmost_depth(offers_data, add_quantity)
        reduce_quantity_from_topmost_depth(bids_data, add_quantity)

        if len(bids_data) == 0 or len(offers_data) == 0:
            break

    return {'buy_price': buy_price, 'sell_price': sell_price, 'quantity': quantity}


def save_arbitrage_opportunities(arbitrage_opportunities):
    if not arbitrage_opportunities:
        return;

    add_all(arbitrage_opportunities)
