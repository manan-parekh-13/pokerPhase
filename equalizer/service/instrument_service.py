from Models.arbitrage_instruments import ArbitrageInstruments
from kiteconnect.utils import get_env_variable
from kiteconnect.global_stuff import get_kite_client_from_cache, get_product_int_for_product_type
from copy import deepcopy

useCython = get_env_variable("USE_CYTHON_FUNC")
if useCython == "yes":
    from cython.cython_functions_c import get_threshold_spread_coef_for_reqd_profit
else:
    from equalizer.service.charges_service import get_threshold_spread_coef_for_reqd_profit

MAX_TOKENS_PER_WEB_SOCKET = 500


def get_ws_id_to_token_to_instrument_map():
    instruments = ArbitrageInstruments.get_arbitrage_instruments()
    ws_id_to_token_to_instrument_map = {}
    web_socket_index_map = {}
    kite_client = get_kite_client_from_cache()

    default_buy_value = kite_client.get_available_margin() or get_env_variable('DEFAULT_MARGIN_FOR_CHECKING')

    for instrument in instruments:
        if not instrument.product_type or not isinstance(instrument.product_type, list):
            raise ValueError("Product type not supported for instrument with id: {} and symbol: {}"
                             .format(instrument.id, instrument.trading_symbol))

        instrument1 = deepcopy(instrument)
        instrument1.equivalent_token = instrument.instrument_token2

        instrument2 = deepcopy(instrument)
        instrument2.equivalent_token = instrument.instrument_token1

        # regardless of status of instrument, we need to have data web socket for every instrument token
        if not web_socket_index_map.get('data'):
            web_socket_index_map['data'] = 0

        data_ws_id = "data_{}".format(web_socket_index_map['data'])
        if data_ws_id not in ws_id_to_token_to_instrument_map:
            ws_id_to_token_to_instrument_map[data_ws_id] = {}
        ws_id_to_token_to_instrument_map[data_ws_id][instrument1.instrument_token1] = instrument1
        ws_id_to_token_to_instrument_map[data_ws_id][instrument2.instrument_token2] = instrument2

        if len(ws_id_to_token_to_instrument_map[data_ws_id]) >= MAX_TOKENS_PER_WEB_SOCKET:
            web_socket_index_map['data'] += 1

        status = "order" if instrument.try_ordering else "check"

        for product in instrument.product_type:
            instrument1.product_type = product
            instrument2.product_type = product

            product_and_status = "{}_{}".format(product, status)
            if not web_socket_index_map.get(product_and_status):
                web_socket_index_map[product_and_status] = 0

            ws_id = "{}_{}".format(product_and_status, web_socket_index_map[product_and_status])
            if ws_id not in ws_id_to_token_to_instrument_map:
                ws_id_to_token_to_instrument_map[ws_id] = {}

            instrument1.ws_id = ws_id
            instrument2.ws_id = ws_id

            product_type_int = get_product_int_for_product_type(product)

            threshold_spread_coef = get_threshold_spread_coef_for_reqd_profit(buy_value=int(default_buy_value),
                                                                              profit_percent=instrument.min_profit_percent,
                                                                              product_type_int=product_type_int)
            instrument1.threshold_spread_coef = threshold_spread_coef
            instrument2.threshold_spread_coef = threshold_spread_coef

            instrument1.product_type_int = product_type_int
            instrument2.product_type_int = product_type_int

            instrument1.exchange = instrument1.exchange1
            instrument2.exchange = instrument2.exchange2

            del instrument1.exchange1
            del instrument2.exchange1

            del instrument1.exchange2
            del instrument2.exchange2

            ws_id_to_token_to_instrument_map[instrument1.ws_id][instrument1.instrument_token1] = instrument1
            ws_id_to_token_to_instrument_map[instrument2.ws_id][instrument2.instrument_token2] = instrument2

            if len(ws_id_to_token_to_instrument_map[ws_id]) >= MAX_TOKENS_PER_WEB_SOCKET:
                web_socket_index_map[product_and_status] += 1

    return ws_id_to_token_to_instrument_map
