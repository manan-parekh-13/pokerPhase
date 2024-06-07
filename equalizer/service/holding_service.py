from Models.holdings import Holdings


def get_holdings_available_for_arbitrage_in_map():
    available_holdings = Holdings.get_holdings_available_for_arbitrage()
    if not available_holdings:
        return None

    available_holdings_map = {}
    for holding in available_holdings:
        if holding.arbitrage_quantity == 0:
            continue
        if holding.arbitrage_quantity > holding.realised_quantity:
            continue
        available_holdings_map[holding.tradingsymbol] = holding.arbitrage_quantity

    return available_holdings_map
