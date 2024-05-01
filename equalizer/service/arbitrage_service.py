from Models.arbitrageOpportunity import init_arbitrage_opportunities
from Models.arbitrage_instruments import ArbitrageInstruments
from mysql_config import add_all

from datetime import datetime
from copy import deepcopy


def check_arbitrage(ticker1, ticker2, threshold_percentage, buy_threshold):

    arbitrage_opportunities = []

    # strategy 1 - buy from ticker2 and sell in ticker1
    ticker1_bids = deepcopy(ticker1)['depth']['buy']
    ticker2_offers = deepcopy(ticker2)['depth']['sell']
    result1 = get_price_and_quantity_for_arbitrage(bids_data=ticker1_bids, offers_data=ticker2_offers, threshold_percentage=threshold_percentage)

    if result1['buy_price'] * result1['quantity'] >= buy_threshold:
        sell_price = result1['sell_price']
        buy_price = result1['buy_price']
        quantity = result1['quantity']
        profit_percent = (sell_price - buy_price) * 100 / buy_price
        arbitrage_opportunities.append(init_arbitrage_opportunities(buy_source=ticker2['instrument_token'],
                                                                    sell_source=ticker1['instrument_token'],
                                                                    quantity=quantity,
                                                                    buy_price=buy_price,
                                                                    sell_price=sell_price,
                                                                    buy_source_ticker_time=ticker2[
                                                                        'exchange_timestamp'],
                                                                    sell_source_ticker_time=ticker1[
                                                                        'exchange_timestamp'],
                                                                    buy_threshold=buy_threshold,
                                                                    threshold_percentage=threshold_percentage,
                                                                    profit_percent=profit_percent,
                                                                    buy_value=buy_price * quantity,
                                                                    created_at=datetime.now()))

    # strategy 2 - buy from ticker1 and sell in ticker2
    ticker2_bids = deepcopy(ticker2)['depth']['buy']
    ticker1_offers = deepcopy(ticker1)['depth']['sell']
    result2 = get_price_and_quantity_for_arbitrage(bids_data=ticker2_bids, offers_data=ticker1_offers, threshold_percentage=threshold_percentage)

    if result2['buy_price'] * result2['quantity'] >= buy_threshold:
        sell_price = result2['sell_price']
        buy_price = result2['buy_price']
        quantity = result2['quantity']
        profit_percent = (sell_price - buy_price) * 100 / buy_price
        arbitrage_opportunities.append(init_arbitrage_opportunities(buy_source=ticker1['instrument_token'],
                                                                    sell_source=ticker2['instrument_token'],
                                                                    quantity=quantity,
                                                                    buy_price=buy_price,
                                                                    sell_price=sell_price,
                                                                    buy_source_ticker_time=ticker1[
                                                                        'exchange_timestamp'],
                                                                    sell_source_ticker_time=ticker2[
                                                                        'exchange_timestamp'],
                                                                    buy_threshold=buy_threshold,
                                                                    threshold_percentage=threshold_percentage,
                                                                    profit_percent=profit_percent,
                                                                    buy_value=buy_price * quantity,
                                                                    created_at=datetime.now()))

    return arbitrage_opportunities


def get_price_and_quantity_for_arbitrage(bids_data, offers_data, threshold_percentage):
    if not bids_data or not offers_data:
        return None

    buy_price = 0
    sell_price = 0
    quantity = 0

    while True:
        lowest_buy = offers_data[0]
        highest_sell = bids_data[0]

        spread = highest_sell['price'] - lowest_buy['price']
        spread_percentage = spread * 100 / lowest_buy['price'] if lowest_buy['price'] > 0 else 0

        if spread_percentage < threshold_percentage:
            break

        buy_price = lowest_buy['price']
        sell_price = highest_sell['price']

        if lowest_buy['quantity'] > highest_sell['quantity']:
            quantity += highest_sell['quantity']
            offers_data[0]['quantity'] = lowest_buy['quantity'] - highest_sell['quantity']
            bids_data.pop(0)
        elif lowest_buy['quantity'] < highest_sell['quantity']:
            quantity += lowest_buy['quantity']
            bids_data[0]['quantity'] = highest_sell['quantity'] - lowest_buy['quantity']
            offers_data.pop(0)
        else:
            quantity += lowest_buy['quantity']
            bids_data.pop(0)
            offers_data.pop(0)

        if len(bids_data) == 0 or len(offers_data) == 0:
            break

    return {'buy_price': buy_price, 'sell_price': sell_price, 'quantity': quantity}


def save_arbitrage_opportunities(arbitrage_opportunities):
    if not arbitrage_opportunities:
        return;

    add_all(arbitrage_opportunities)


def get_instrument_token_map_for_arbitrage():
    instruments = ArbitrageInstruments.get_instruments_by_check_for_opportunity(True)
    token_to_instrument_map = {}
    for instrument in instruments:
        instrument1 = deepcopy(instrument)
        instrument1.equivalent_token = instrument.instrument_token2
        token_to_instrument_map[instrument.instrument_token1] = instrument1

        instrument2 = deepcopy(instrument)
        instrument2.equivalent_token = instrument.instrument_token1
        token_to_instrument_map[instrument.instrument_token2] = instrument2
    return token_to_instrument_map
