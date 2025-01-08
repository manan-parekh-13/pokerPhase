from kiteconnect.global_stuff import get_latest_tick_by_instrument_token_from_global_cache


def is_ticker_stale(ticker):
    latest_ticker_for_instrument = get_latest_tick_by_instrument_token_from_global_cache(ticker['instrument_token'])
    return latest_ticker_for_instrument['ticker_received_time'] > ticker['ticker_received_time']


def is_opportunity_stale(opportunity):
    latest_tick_for_buy_source = get_latest_tick_by_instrument_token_from_global_cache(opportunity.buy_source)
    if latest_tick_for_buy_source['ticker_received_time'] > opportunity.buy_source_ticker_time:
        return True

    latest_tick_for_sell_source = get_latest_tick_by_instrument_token_from_global_cache(opportunity.sell_source)
    if latest_tick_for_sell_source['ticker_received_time'] > opportunity.sell_source_ticker_time:
        return True

    return False
