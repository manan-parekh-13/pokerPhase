from Models.holdings import Holdings
from equalizer.web import global_cache


def get_holdings_available_for_arbitrage_in_map():
    instrument_token_map = global_cache['instrument_map']

    available_holdings = Holdings.get_holdings_available_for_arbitrage()
    if not available_holdings:
        return None

    available_holdings_map = {}
    for holding in available_holdings:
        if holding.arbitrage_quantity == 0:
            continue
        if holding.arbitrage_quantity > holding.realised_quantity:
            continue
        available_holdings_map[holding.instrument_token] = holding.arbitrage_quantity
        # set the same quantity for equivalent too
        equivalent_token = instrument_token_map[holding.instrument_token]['equivalent_token']
        available_holdings_map[equivalent_token] = holding.arbitrage_quantity

    return available_holdings_map
