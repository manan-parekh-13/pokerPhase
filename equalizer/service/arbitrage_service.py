from Models.arbitrageOpportunity import init_arbitrage_opportunities
from mysql_config import add_all

from datetime import datetime


def check_arbitrage(ticker1, ticker2, threshold_percentage, buy_threshold):

    arbitrage_opportunities = []

    # strategy 1 - buy from ticker1 and sell in ticker2
    buy_depth_ticker1 = ticker1['depth']['buy']
    sell_depth_ticker2 = ticker2['depth']['sell']
    result1 = get_price_and_quantity_for_arbitrage(buy_depth_ticker1, sell_depth_ticker2, threshold_percentage)

    if result1['buy_price'] * result1['quantity'] >= buy_threshold:
        sell_price = result1['sell_price']
        buy_price = result1['buy_price']
        quantity = result1['quantity']
        profit_percent = ( sell_price - buy_price ) * 100 / buy_price
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

    # strategy 2 - buy from ticker2 and sell in ticker1
    buy_depth_ticker2 = ticker2['depth']['buy']
    sell_depth_ticker1 = ticker1['depth']['sell']
    result2 = get_price_and_quantity_for_arbitrage(buy_depth_ticker2, sell_depth_ticker1, threshold_percentage)

    if result2['buy_price'] * result2['quantity'] >= buy_threshold:
        sell_price = result2['sell_price']
        buy_price = result2['buy_price']
        quantity = result2['quantity']
        profit_percent = ( sell_price - buy_price ) * 100 / buy_price
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

    return arbitrage_opportunities


def get_price_and_quantity_for_arbitrage(buy_depth_data, sell_depth_data, threshold_percentage):
    if not buy_depth_data or not sell_depth_data:
        return None

    buy_price = 0
    sell_price = 0
    quantity = 0

    while True:
        best_buy = sell_depth_data[0]
        best_sell = buy_depth_data[0]

        spread = best_sell['price'] - best_buy['price']
        spread_percentage = spread * 100 / best_buy['price'] if best_buy['price'] > 0 else 0

        if spread_percentage < threshold_percentage:
            break

        buy_price = best_buy['price']
        sell_price = best_sell['price']

        if best_buy['quantity'] > best_sell['quantity']:
            quantity += best_sell['quantity']
            buy_depth_data[0]['quantity'] = best_buy['quantity'] - best_sell['quantity']
            sell_depth_data.pop(0)
        elif best_buy['quantity'] < best_sell['quantity']:
            quantity += best_buy['quantity']
            sell_depth_data[0]['quantity'] = best_sell['quantity'] - best_buy['quantity']
            buy_depth_data.pop(0)
        else:
            quantity += best_sell['quantity']
            sell_depth_data.pop(0)
            buy_depth_data.pop(0)

        if len(buy_depth_data) == 0 or len(sell_depth_data) == 0:
            break

    return {'buy_price': buy_price, 'sell_price': sell_price, 'quantity': quantity}


def save_arbitrage_opportunities(arbitrage_opportunities):
    if not arbitrage_opportunities:
        return;

    add_all(arbitrage_opportunities)


