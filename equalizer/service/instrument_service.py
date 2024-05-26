from Models.arbitrage_instruments import ArbitrageInstruments


def get_token_to_arbitrage_instrument_map():
    instruments = ArbitrageInstruments.get_instruments_with_non_null_ws_id()
    if not instruments:
        return None

    instrument_map = {}
    for instrument in instruments:
        instrument_map[instrument.instrument_token1] = {
            'trading_symbol': instrument.trading_symbol,
            'exchange': instrument.exchange1,
            'equivalent_token': instrument.instrument_token2
        }
        instrument_map[instrument.instrument_token2] = {
            'trading_symbol': instrument.trading_symbol,
            'exchange': instrument.exchange2,
            'equivalent_token': instrument.instrument_token1
        }
    return instrument_map
