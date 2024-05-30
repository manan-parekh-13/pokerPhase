from Models.arbitrage_opportunity import init_arbitrage_opportunities
from Models.arbitrage_instruments import ArbitrageInstruments
from mysql_config import add_all
from equalizer.service.charges_service import get_min_percentage_reqd_for_min_profit
from equalizer.service.ticker_service import reduce_quantity_from_topmost_depth
from kiteconnect.login import set_timezone_in_datetime
from datetime import datetime
from copy import deepcopy


def check_arbitrage(ticker1, ticker2, ltp, min_profit_percent, product_type, max_buy_quantity, ws_id):
    # strategy 1 - buy from ticker2 and sell in ticker1
    ticker1_bids = deepcopy(ticker1)['depth']['buy']
    ticker2_offers = deepcopy(ticker2)['depth']['sell']

    result1 = get_price_and_quantity_for_arbitrage(bids_data=ticker1_bids,
                                                   offers_data=ticker2_offers,
                                                   min_prof_coef=min_profit_percent / 100,
                                                   max_buy_quantity=max_buy_quantity,
                                                   ltp=ltp,
                                                   product_type=product_type)

    if result1['quantity'] > 0:
        # In case strategy 1 has opportunities, no need to try strategy 2
        return init_arbitrage_opportunities(buy_source=ticker2['instrument_token'],
                                            sell_source=ticker1['instrument_token'],
                                            quantity=result1['quantity'],
                                            buy_price=result1['buy_price'],
                                            sell_price=result1['sell_price'],
                                            buy_source_ticker_time=ticker2[
                                                'ticker_received_time'],
                                            sell_source_ticker_time=ticker1[
                                                'ticker_received_time'],
                                            created_at=set_timezone_in_datetime(datetime.now()),
                                            ws_id=ws_id)

    # In case strategy 2's highest sell price > the lowest buy price, no need to try strategy 2
    if ticker2['depth']['sell'][0]['price'] < ticker1['depth']['buy'][0]['price']:
        return None

    # strategy 2 - buy from ticker1 and sell in ticker2
    ticker2_bids = deepcopy(ticker2)['depth']['buy']
    ticker1_offers = deepcopy(ticker1)['depth']['sell']
    result2 = get_price_and_quantity_for_arbitrage(bids_data=ticker2_bids,
                                                   offers_data=ticker1_offers,
                                                   min_prof_coef=min_profit_percent / 100,
                                                   max_buy_quantity=max_buy_quantity,
                                                   ltp=ltp,
                                                   product_type=product_type)

    if result2['quantity'] > 0:
        return init_arbitrage_opportunities(buy_source=ticker1['instrument_token'],
                                            sell_source=ticker2['instrument_token'],
                                            quantity=result2['quantity'],
                                            buy_price=result2['buy_price'],
                                            sell_price=result2['sell_price'],
                                            buy_source_ticker_time=ticker1[
                                                'ticker_received_time'],
                                            sell_source_ticker_time=ticker2[
                                                'ticker_received_time'],
                                            created_at=set_timezone_in_datetime(datetime.now()),
                                            ws_id=ws_id)

    return None


def get_price_and_quantity_for_arbitrage(bids_data, offers_data, min_prof_coef, max_buy_quantity, ltp, product_type):
    buy_price = 0
    sell_price = 0
    quantity = 0

    while True:
        lowest_buy = offers_data[0]
        highest_sell = bids_data[0]

        buy_price = lowest_buy['price']
        sell_price = highest_sell['price']

        threshold_spread_coef = get_min_percentage_reqd_for_min_profit(max_buy_value=max_buy_quantity * ltp,
                                                                       min_profit_coef=min_prof_coef,
                                                                       product_type=product_type)

        spread_coef = sell_price - buy_price / buy_price if buy_price > 0 else 0

        if spread_coef < threshold_spread_coef:
            break

        add_quantity = min(lowest_buy['quantity'], highest_sell['quantity'])
        quantity = min(quantity + add_quantity, max_buy_quantity)
        if quantity == max_buy_quantity or quantity == 0:
            break;

        reduce_quantity_from_topmost_depth(offers_data, add_quantity)
        reduce_quantity_from_topmost_depth(bids_data, add_quantity)

        if len(bids_data) == 0 or len(offers_data) == 0:
            break

    if quantity != max_buy_quantity:
        threshold_spread_coef = get_min_percentage_reqd_for_min_profit(max_buy_value=quantity * ltp,
                                                                       min_profit_coef=min_prof_coef,
                                                                       product_type=product_type)
        spread_coef = sell_price - buy_price / buy_price
        quantity = quantity if spread_coef > threshold_spread_coef else 0

    return {'buy_price': buy_price, 'sell_price': sell_price, 'quantity': quantity}


def save_arbitrage_opportunities(arbitrage_opportunities):
    if not arbitrage_opportunities:
        return;

    add_all(arbitrage_opportunities)


def get_ws_id_to_token_to_instrument_map():
    instruments = ArbitrageInstruments.get_instruments_with_non_null_ws_id()
    ws_id_to_token_to_instrument_map = {}

    for instrument in instruments:
        instrument1 = deepcopy(instrument)
        instrument1.equivalent_token = instrument.instrument_token2

        if instrument1.ws_id not in ws_id_to_token_to_instrument_map:
            ws_id_to_token_to_instrument_map[instrument1.ws_id] = {}
        ws_id_to_token_to_instrument_map[instrument1.ws_id][instrument1.instrument_token1] = instrument1

        instrument2 = deepcopy(instrument)
        instrument2.equivalent_token = instrument.instrument_token1

        if instrument2.ws_id not in ws_id_to_token_to_instrument_map:
            ws_id_to_token_to_instrument_map[instrument2.ws_id] = {}
        ws_id_to_token_to_instrument_map[instrument2.ws_id][instrument2.instrument_token2] = instrument2

    return ws_id_to_token_to_instrument_map
