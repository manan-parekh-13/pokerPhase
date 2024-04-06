from Models.arbitrageOpportunity import init_arbitrage_opportunities
from mysql_config import add_all


def check_arbitrage(ticker1, ticker2, ticker1_source, ticker2_source, threshold_percentage, buy_threshold):
    # Extract the first depth data for buy and sell orders for each ticker
    buy_order_ticker1 = ticker1['depth']['buy'][0]
    sell_order_ticker1 = ticker1['depth']['sell'][0]

    buy_order_ticker2 = ticker2['depth']['buy'][0]
    sell_order_ticker2 = ticker2['depth']['sell'][0]

    # Calculate the spreads for each ticker
    spread_ticker1 = sell_order_ticker2['price'] - buy_order_ticker1['price']
    spread_ticker2 = sell_order_ticker1['price'] - buy_order_ticker2['price']

    spread_percentage_change_ticker1 = spread_ticker1 * 100 / buy_order_ticker1['price']
    spread_percentage_change_ticker2 = spread_ticker2 * 100 / buy_order_ticker2['price']

    if spread_percentage_change_ticker1 < threshold_percentage and spread_percentage_change_ticker2 < threshold_percentage:
        return

    spread_value_ticker1 = 0
    spread_value_ticker2 = 0
    quantity_ticker1 = 0
    quantity_ticker2 = 0

    if spread_percentage_change_ticker1 > threshold_percentage:
        quantity_ticker1 = min(buy_order_ticker1['quantity'], sell_order_ticker2['quantity'])
        spread_value_ticker1 = buy_order_ticker1['price'] * quantity_ticker1

    if spread_percentage_change_ticker2 > threshold_percentage:
        quantity_ticker2 = min(buy_order_ticker2['quantity'], sell_order_ticker1['quantity'])
        spread_value_ticker2 = buy_order_ticker2['price'] * quantity_ticker2

    arbitrage_opportunities = []

    if spread_value_ticker1 > buy_threshold:
        arbitrage_opportunities.append(init_arbitrage_opportunities(buy_source=ticker1_source,
                                                                    sell_source=ticker2_source,
                                                                    quantity=quantity_ticker1,
                                                                    buy_price=buy_order_ticker1['price'],
                                                                    sell_price=sell_order_ticker2['price'],
                                                                    buy_source_ticker_time=ticker1['exchange_timestamp'],
                                                                    sell_source_ticker_time=ticker2['exchange_timestamp'],
                                                                    buy_threshold=buy_threshold,
                                                                    threshold_percentage=threshold_percentage,
                                                                    profit_percent=spread_percentage_change_ticker1,
                                                                    buy_value=spread_value_ticker1))

    if spread_value_ticker2 > buy_threshold:
        arbitrage_opportunities.append(init_arbitrage_opportunities(buy_source=ticker2_source,
                                                                    sell_source=ticker1_source,
                                                                    quantity=quantity_ticker2,
                                                                    buy_price=buy_order_ticker2['price'],
                                                                    sell_price=sell_order_ticker1['price'],
                                                                    buy_source_ticker_time=ticker2['exchange_timestamp'],
                                                                    sell_source_ticker_time=ticker1['exchange_timestamp'],
                                                                    buy_threshold=buy_threshold,
                                                                    threshold_percentage=threshold_percentage,
                                                                    profit_percent=spread_percentage_change_ticker2,
                                                                    buy_value=spread_value_ticker2))

    return arbitrage_opportunities


def save_arbitrage_opportunities(arbitrage_opportunities):
    if not arbitrage_opportunities:
        return;

    add_all(arbitrage_opportunities)


