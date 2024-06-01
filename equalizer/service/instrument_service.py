from Models.arbitrage_instruments import ArbitrageInstruments
from kiteconnect.utils import get_env_variable
from kiteconnect.login import global_cache
from copy import deepcopy
from equalizer.service.charges_service import get_threshold_spread_coef_for_reqd_profit


def get_instrument_token_to_equivalent_map():
    instruments = ArbitrageInstruments.get_instruments_with_non_null_ws_id()
    if not instruments:
        return None

    token_to_equivalent_map = {}
    for instrument in instruments:
        if instrument.instrument_token1 not in token_to_equivalent_map:
            token_to_equivalent_map[instrument.instrument_token1] = {
                'trading_symbol': instrument.trading_symbol,
                'exchange': instrument.exchange1,
                'equivalent_token': instrument.instrument_token2
            }
        if instrument.instrument_token2 not in token_to_equivalent_map:
            token_to_equivalent_map[instrument.instrument_token2] = {
                'trading_symbol': instrument.trading_symbol,
                'exchange': instrument.exchange2,
                'equivalent_token': instrument.instrument_token1
            }
    return token_to_equivalent_map


def get_ws_id_to_token_to_instrument_map():
    instruments = ArbitrageInstruments.get_instruments_with_non_null_ws_id()
    ws_id_to_token_to_instrument_map = {}

    default_buy_value = global_cache['initial_margin'] or get_env_variable('DEFAULT_MARGIN_FOR_CHECKING')

    for instrument in instruments:
        # save threshold spread coefficient for further use
        threshold_spread_coef = get_threshold_spread_coef_for_reqd_profit(buy_value=default_buy_value,
                                                                          profit_percent=instrument.min_profit_percent,
                                                                          product_type=instrument.product_type)
        instrument.threshold_spread_coef = threshold_spread_coef

        # entry for instrument_token
        instrument1 = deepcopy(instrument)
        instrument1.equivalent_token = instrument.instrument_token2

        if instrument1.ws_id not in ws_id_to_token_to_instrument_map:
            ws_id_to_token_to_instrument_map[instrument1.ws_id] = {}

        ws_id_to_token_to_instrument_map[instrument1.ws_id][instrument1.instrument_token1] = instrument1

        # entry for instrument_token's equivalent
        instrument2 = deepcopy(instrument)
        instrument2.equivalent_token = instrument.instrument_token1

        if instrument2.ws_id not in ws_id_to_token_to_instrument_map:
            ws_id_to_token_to_instrument_map[instrument2.ws_id] = {}
        ws_id_to_token_to_instrument_map[instrument2.ws_id][instrument2.instrument_token2] = instrument2

    return ws_id_to_token_to_instrument_map
