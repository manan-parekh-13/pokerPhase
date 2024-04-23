from Models.arbitrageOpportunity import init_arbitrage_opportunities
from mysql_config import add_all

from datetime import datetime


def check_arbitrage(ticker1, ticker2, threshold_percentage, buy_threshold):

    arbitrage_opportunities = []

    # strategy 1 - buy from ticker2 and sell in ticker1
    ticker1_bids = ticker1['depth']['buy']
    ticker2_offers = ticker2['depth']['sell']
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
    ticker2_bids = ticker2['depth']['buy']
    ticker1_offers = ticker1['depth']['sell']
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


def test_check_arbitrage():
    ticker1 = {
            'instrument_token': 2452737,
            'mode': 'full',
            'last_price': 1885.55,
            'tradable': True,
            'exchange_timestamp': datetime(2024, 4, 12, 11, 41, 54),
            'depth': {
                'buy': [{
                    'price': 1886.45,
                    'quantity': 1486
                }, {
                    'price': 1886.25,
                    'quantity': 1
                }, {
                    'price': 1886.15,
                    'quantity': 45
                }, {
                    'price': 1886.1,
                    'quantity': 9
                }],
                'sell': [{
                    'price': 1886.8,
                    'quantity': 30
                }, {
                    'price': 1886.85,
                    'quantity': 30
                }, {
                    'price': 1886.9,
                    'quantity': 10
                }, {
                    'price': 1886.95,
                    'quantity': 50
                }, {
                    'price': 1887,
                    'quantity': 451
                }]
            }
        }

    ticker2 = {
        'instrument_token': 138918404,
        'mode': 'full',
        'last_price': 1885,
        'tradable': True,
        'exchange_timestamp': datetime(2024, 4, 12, 11, 41, 54),
        'depth': {
            'buy': [{
                'price': 1882.85,
                'quantity': 35
            }, {
                'price': 1882.8,
                'quantity': 27
            }, {
                'price': 1882.55,
                'quantity': 36
            }, {
                'price': 1882.3,
                'quantity': 16
            }, {
                'price': 1882.05,
                'quantity': 16
            }],
            'sell': [{
                'price': 1884.5,
                'quantity': 10
            }, {
                'price': 1884.55,
                'quantity': 12
            }, {
                'price': 1884.9,
                'quantity': 7
            }]
        }
    }
    arbitrage_opportunities = check_arbitrage(ticker1, ticker2, 0, 1)
    print(arbitrage_opportunities)
    return arbitrage_opportunities
