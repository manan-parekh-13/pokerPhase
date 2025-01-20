from datetime import datetime
from typing import Dict, Union, List
from Models.arbitrage_opportunity import init_arbitrage_opportunities_from_strat_res_and_tickers
from equalizer.service.ticker_service import get_equivalent_tick_from_token, get_instrument_from_token
from mysql_config import add
from kiteconnect.global_stuff import add_buy_and_sell_task_to_queue
from kiteconnect.utils import get_product_type_from_ws_id, convert_date_time_to_us
from Models.raw_ticker_data import init_raw_ticker_data


def get_threshold_spread_coef_for_reqd_profit(double buy_value, double profit_percent, int product_type_int):
    cdef double profit_coef = profit_percent / 100.0

    if product_type_int == 2: # PRODUCT_CNC_INT
        return ((15.93 + 0.002241 * buy_value) * (1 + profit_coef)) / buy_value + profit_coef
    elif product_type_int == 1 and buy_value > 66000.0: # PRODUCT_MIS_INT
        return ((47.2 + 0.00038 * buy_value) * (1 + profit_coef)) / buy_value + profit_coef
    elif product_type_int == 1 and buy_value <= 66000.0: # PRODUCT_MIS_INT
        return ((0.0011 * buy_value) * (1 + profit_coef)) / buy_value + profit_coef
    return 0.0

def save_aggregate_data_for_tickers(
    existing_aggregate_data: Dict[int, Dict[str, Any]],
    new_ticks: Dict[int, Dict[str, Any]]
) -> None:
    cdef int instrument_token
    cdef dict latest_tick_for_instrument, prev_ticker_for_instrument

    for instrument_token, latest_tick_for_instrument in new_ticks.items():
        if instrument_token in existing_aggregate_data:
            prev_ticker_for_instrument = existing_aggregate_data.get(instrument_token)
            existing_aggregate_data[instrument_token] = get_new_aggregate_data_from_pre_value(
                prev_ticker_for_instrument
            )
        else:
            existing_aggregate_data[instrument_token] = {
                'ticker_time': datetime.now().timestamp(),
                'started_at': datetime.now().timestamp()
            }

def get_new_aggregate_data_from_pre_value(
    prev_ticker_for_instrument: Dict[str, Union[float, int, str]]
) -> Dict[str, Union[float, int, str]]:
    cdef float current_time = datetime.now().timestamp()
    cdef float new_time_diff = current_time - prev_ticker_for_instrument['ticker_time']

    cdef float new_min
    if 'min' in prev_ticker_for_instrument:
        new_min = min(new_time_diff, prev_ticker_for_instrument['min'])
    else:
        new_min = new_time_diff

    cdef float new_max
    if 'max' in prev_ticker_for_instrument:
        new_max = max(new_time_diff, prev_ticker_for_instrument['max'])
    else:
        new_max = new_time_diff

    cdef int new_n = (prev_ticker_for_instrument.get('n') or 0) + 1
    cdef float new_sum_of_time_diff = (prev_ticker_for_instrument.get('sum_of_time_diff') or 0) + new_time_diff
    cdef float new_sum_of_square_of_time_diff = (prev_ticker_for_instrument.get('sum_of_square_of_time_diff') or 0) + new_time_diff ** 2

    return {
        'started_at': prev_ticker_for_instrument['started_at'],
        'ticker_time': current_time,
        'min': new_min,
        'max': new_max,
        'n': new_n,
        'sum_of_time_diff': new_sum_of_time_diff,
        'sum_of_square_of_time_diff': new_sum_of_square_of_time_diff
    }

def check_arbitrage(ticker1, ticker2, threshold_spread_coef, min_profit_percent,
                    product_type_int, max_buy_quantity, ws_id):
    # strategy 1 - buy from ticker2 and sell in ticker1
    strat_1_result = get_price_and_quantity_for_arbitrage(
        bids_data=ticker1['depth']['buy'],
        offers_data=ticker2['depth']['sell'],
        threshold_spread_coef=threshold_spread_coef,
        max_buy_quantity=max_buy_quantity
    )

    if strat_1_result['quantity'] > 0 and strat_1_result['buy_price'] > 0:
        spread_coef_for_reqd_profit = get_threshold_spread_coef_for_reqd_profit(
            buy_value=strat_1_result['quantity'] * strat_1_result['buy_price'],
            profit_percent=min_profit_percent,
            product_type_int=product_type_int
        )

        spread_coef = (strat_1_result['sell_price'] / strat_1_result['buy_price']) - 1
        if spread_coef >= spread_coef_for_reqd_profit:
            return init_arbitrage_opportunities_from_strat_res_and_tickers(
                buy_ticker=ticker2,
                sell_ticker=ticker1,
                strat_result=strat_1_result,
                ws_id=ws_id
            )

    # strategy 2 - buy from ticker1 and sell in ticker2
    strat_2_result = get_price_and_quantity_for_arbitrage(
        bids_data=ticker2['depth']['buy'],
        offers_data=ticker1['depth']['sell'],
        threshold_spread_coef=threshold_spread_coef,
        max_buy_quantity=max_buy_quantity
    )

    if strat_2_result['quantity'] > 0 and strat_2_result['buy_price'] > 0:
        spread_coef_for_reqd_profit = get_threshold_spread_coef_for_reqd_profit(
            buy_value=strat_2_result['quantity'] * strat_2_result['buy_price'],
            profit_percent=min_profit_percent,
            product_type_int=product_type_int
        )

        spread_coef = (strat_2_result['sell_price'] / strat_2_result['buy_price']) - 1
        if spread_coef >= spread_coef_for_reqd_profit:
            return init_arbitrage_opportunities_from_strat_res_and_tickers(
                buy_ticker=ticker1,
                sell_ticker=ticker2,
                strat_result=strat_2_result,
                ws_id=ws_id
            )

    return None


cdef dict get_price_and_quantity_for_arbitrage(list bids_data, list offers_data,
                                                double threshold_spread_coef, double max_buy_quantity):
    cdef double quantity = 0
    cdef int current_offers_depth = 0
    cdef int current_bids_depth = 0
    cdef double buy_price, sell_price, spread_coef
    cdef double add_quantity

    while True:
        lowest_buy = offers_data[current_offers_depth]
        highest_sell = bids_data[current_bids_depth]

        buy_price = lowest_buy['price']
        sell_price = highest_sell['price']
        spread_coef = (sell_price - buy_price) / buy_price if buy_price > 0 else 0

        if spread_coef < threshold_spread_coef:
            break

        add_quantity = min(lowest_buy['left_quantity'], highest_sell['left_quantity'])
        quantity = min(quantity + add_quantity, max_buy_quantity)

        if quantity == max_buy_quantity or quantity == 0:
            break

        offers_data[current_offers_depth]['left_quantity'] -= add_quantity
        if offers_data[current_offers_depth]['left_quantity'] == 0:
            current_offers_depth += 1

        bids_data[current_bids_depth]['left_quantity'] -= add_quantity
        if bids_data[current_bids_depth]['left_quantity'] == 0:
            current_bids_depth += 1

        if current_offers_depth == 5 or current_bids_depth == 5:
            break

    return {'buy_price': buy_price, 'sell_price': sell_price, 'quantity': quantity}

def check_tickers_for_arbitrage(
    ticks: Dict[int, Dict[str, Any]],
    tickers_to_be_saved: List[Dict[str, Any]],
    web_socket: Any,
    kite_client: Any
) -> None:
    cdef int instrument_token, max_buy_quantity
    cdef dict latest_tick_for_instrument, latest_tick_for_equivalent
    cdef float ltp, available_margin, reqd_margin
    cdef long opportunity_check_started_at
    cdef object instrument, opportunity

    for instrument_token, latest_tick_for_instrument in ticks.items():
        opportunity_check_started_at = convert_date_time_to_us(datetime.now())

        latest_tick_for_equivalent = get_equivalent_tick_from_token(web_socket, instrument_token)

        if not latest_tick_for_equivalent:
            continue

        ltp = latest_tick_for_instrument['depth']['sell'][0]['price']

        if ltp == 0.0:
            continue

        instrument = get_instrument_from_token(web_socket, instrument_token)

        available_margin = kite_client.get_available_margin()
        max_buy_quantity = int(available_margin / ltp)

        if max_buy_quantity == 0:
            continue

        opportunity = check_arbitrage(
            latest_tick_for_equivalent,
            latest_tick_for_instrument,
            instrument.threshold_spread_coef,
            instrument.min_profit_percent,
            instrument.product_type,
            max_buy_quantity,
            web_socket.ws_id
        )

        if not opportunity:
            continue

        opportunity.opportunity_check_started_at = opportunity_check_started_at
        instrument.leverage = instrument.leverage if instrument.leverage else 1

        if not web_socket.try_ordering:
            add(opportunity)
            continue

        reqd_margin = (opportunity.buy_price + opportunity.sell_price) * opportunity.quantity / instrument.leverage

        add_buy_and_sell_task_to_queue({
            "opportunity": opportunity,
            "product_type": get_product_type_from_ws_id(opportunity.ws_id),
            "reqd_margin": reqd_margin,
            "leverage": instrument.leverage
        })

        tickers_to_be_saved.append(init_raw_ticker_data(latest_tick_for_instrument, web_socket.ws_id))
        tickers_to_be_saved.append(init_raw_ticker_data(latest_tick_for_equivalent, web_socket.ws_id))