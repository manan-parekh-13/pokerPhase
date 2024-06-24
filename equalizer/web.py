import logging
import threading
import traceback
from flask import Flask, jsonify, request, abort
from kiteconnect.login import login_via_enc_token, login_via_two_f_a
from kiteconnect.utils import get_env_variable
from kiteconnect.global_stuff import (init_latest_tick_data_in_global_cache, init_aggregate_data_for_ws_in_global_cache,
                                      init_instrument_token_to_equivalent_token_map, get_kite_client_from_cache)
from service.socket_service import init_kite_web_socket, send_web_socket_updates
from service.instrument_service import get_ws_id_to_token_to_instrument_map
from service.instrument_service import get_instrument_token_to_equivalent_map
from environment.loader import load_environment
from mysql_config import add_all
from Models import instrument
from kiteconnect.utils import log_info_and_notify, log_error_and_notify
from service.holding_service import get_holdings_available_for_arbitrage_in_map
import asyncio
from service.order_service import consume_opportunity

# Remove all handlers associated with the root logger object
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)
# Logger settings
logging.basicConfig(
    level=get_env_variable('LOGGING_MODE'),
    format='%(asctime)s|%(levelname)s|%(name)s|%(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Base settings
PORT = 5010
HOST = "127.0.0.1"

# Load the environment configuration
environment = get_env_variable('FLASK_ENV')
load_environment(environment)


# App
app = Flask(__name__)
app.secret_key = 'Yo'


@app.route("/login/otp", methods=['POST'])
def login_via_otp():
    kite = login_via_two_f_a()
    if not kite.enc_token:
        abort(500, "Unable to verify otp / Token not fetched")

    return "Successfully logged in! with enc_token: {}".format(kite.enc_token)


@app.route("/login/enc_token", methods=['POST'])
def login_with_enc_token():
    enc_token = request.form.get('enc_token')
    kite = login_via_enc_token(enc_token)
    if not kite.enc_token:
        abort(500, "Unable to set enc token")
    return "Successfully logged in via enc token"


@app.route("/equalizer/startup", methods=['POST'])
async def start_up_equalizer():
    kite = get_kite_client_from_cache()
    if not kite.enc_token:
        kite = login_via_two_f_a()

    if not kite.enc_token:
        log_info_and_notify("Unable to login")
        abort(500, "Unable to login")

    log_info_and_notify("Successfully logged in!, enc_token: {}".format(kite.enc_token))

    # init the global level data points
    init_latest_tick_data_in_global_cache()
    init_instrument_token_to_equivalent_token_map(get_instrument_token_to_equivalent_map())

    # get and set available margin and holdings in kite_client, along with initial margin in global cache
    usable_margin = 0 if not request.form.get('usable_margin') else int(request.form.get('usable_margin'))
    available_holdings_map = get_holdings_available_for_arbitrage_in_map()
    kite.set_available_margin_and_holdings(new_margins=usable_margin, new_holdings=available_holdings_map)

    log_info_and_notify("Available margin: {} and holdings: {}".format(usable_margin, available_holdings_map))

    logging.debug("main_thread: {}".format(threading.current_thread().name))

    # prepare web socket wise token wise instrument map
    ws_id_to_token_to_instrument_map = get_ws_id_to_token_to_instrument_map()
    has_order_ws = False

    for ws_id in ws_id_to_token_to_instrument_map.keys():
        sub_token_map = ws_id_to_token_to_instrument_map[ws_id]
        try_ordering = True if "order" in ws_id else False
        is_data_ws = True if "data" in ws_id else False

        if try_ordering and (not usable_margin or usable_margin <= 0):
            log_info_and_notify("Ordering not possible for ws_id {} as no margins available".format(ws_id))
            continue

        if try_ordering and (not available_holdings_map):
            log_info_and_notify("Ordering not possible for ws_id {} as no holdings available".format(ws_id))
            continue

        if try_ordering and not has_order_ws:
            has_order_ws = True

        # init the latest aggregate data for this ws_id
        init_aggregate_data_for_ws_in_global_cache(ws_id=ws_id)

        kws = init_kite_web_socket(kite, True, 3, sub_token_map, ws_id, try_ordering, is_data_ws)
        kws.connect(threaded=True)

    # start consumer to realise arbitrage opportunities in case order web sockets exist
    # consumer_task = asyncio.create_task(consume_opportunity())
    # status_update_task = asyncio.create_task(send_web_socket_updates())

    # await asyncio.gather(status_update_task, consumer_task)


@app.route("/holdings.json", methods=['GET'])
def holdings():
    kite = get_kite_client_from_cache()
    response = kite.holdings()
    # if response:
    #     holding_list = []
    #     for holding in response:
    #         holding['arbitrage_quantity'] = None
    #         holding['authorisation'] = json.dumps(holding['authorisation'])
    #         holding_list.append(Holdings(**holding))
    #     add_all(holding_list)
    return jsonify(response)


@app.route("/orders.json", methods=['GET'])
def orders():
    kite = get_kite_client_from_cache()
    response = kite.orders()
    return jsonify(response)


@app.route("/margins.json", methods=['GET'])
def margins():
    kite = get_kite_client_from_cache()
    margin_resp = kite.margins(segment=kite.MARGIN_EQUITY)
    return jsonify(margin_resp)


@app.route("/positions.json", methods=['GET'])
def positions():
    kite = get_kite_client_from_cache()
    position_resp = kite.positions()
    return jsonify(position_resp)


@app.route("/instruments.json", methods=['GET'])
def instruments():
    kite = get_kite_client_from_cache()
    instrument_records = kite.instruments()
    instrument_model_list = instrument.convert_all(instrument_records)
    add_all(instrument_model_list)
    return jsonify(instrument_records)


@app.errorhandler(Exception)
def handle_exception(e):
    stack_trace = traceback.format_exc()
    log_error_and_notify("Trace: {} Error: {}".format(stack_trace, str(e)))
    return jsonify(stack_trace, 500)


if __name__ == "__main__":
    logging.info("Starting server: http://{host}:{port}".format(host=HOST, port=PORT))
    app.run(host=HOST, port=PORT, debug=True)
