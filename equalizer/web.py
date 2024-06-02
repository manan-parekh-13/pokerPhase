import logging
import json

from flask import Flask, jsonify, request, abort

from kiteconnect.login import login_via_enc_token, login_via_two_f_a, get_kite_client_from_cache, global_cache
from kiteconnect.utils import get_env_variable
from service.socket_service import init_kite_web_socket, send_web_socket_updates, get_ws_id_to_web_socket_map
from service.instrument_service import get_ws_id_to_token_to_instrument_map
from service.instrument_service import get_instrument_token_to_equivalent_map
from environment.loader import load_environment
from mysql_config import add_all
from Models import instrument
from Models.holdings import Holdings
from kiteconnect.utils import log_and_notify
from service.holding_service import get_holdings_available_for_arbitrage_in_map

logging.basicConfig(level=logging.DEBUG)

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
def start_up_equalizer():
    kite = get_kite_client_from_cache()
    if not kite.enc_token:
        kite = login_via_two_f_a()

    if not kite.enc_token:
        log_and_notify("Unable to login")
        abort(500, "Unable to login")

    log_and_notify("Successfully logged in!, enc_token: {}".format(kite.enc_token))

    # cache instrument token to its equivalent details for further use
    global_cache['token_to_equivalent_map'] = get_instrument_token_to_equivalent_map()

    # get and set available margin and holdings in kite_client, along with initial margin in global cache
    usable_margin = 0 if not request.form.get('usable_margin') else int(request.form.get('usable_margin'))
    global_cache['initial_margin'] = usable_margin
    available_holdings_map = get_holdings_available_for_arbitrage_in_map()
    kite.set_available_margin_and_holdings(new_margins=usable_margin, new_holdings=available_holdings_map)

    log_and_notify("Available margin: {} and holdings: {}".format(usable_margin, available_holdings_map))

    # prepare web socket wise token wise instrument map
    ws_id_to_token_to_instrument_map = get_ws_id_to_token_to_instrument_map()

    # get web socket meta
    ws_id_to_web_socket_map = get_ws_id_to_web_socket_map()

    for ws_id in ws_id_to_token_to_instrument_map.keys():
        sub_token_map = ws_id_to_token_to_instrument_map[ws_id]
        web_socket = ws_id_to_web_socket_map[ws_id]

        if web_socket.try_ordering and (not usable_margin or usable_margin <= 0):
            log_and_notify("Ordering not possible for ws_id {} as no margins available".format(ws_id))
            continue

        if web_socket.try_ordering and (not available_holdings_map):
            log_and_notify("Ordering not possible for ws_id {} as no holdings available".format(ws_id))
            continue

        kws = init_kite_web_socket(kite, True, 3, sub_token_map, ws_id,
                                   web_socket.mode, web_socket.try_ordering, web_socket.check_for_opportunity)
        kws.connect(threaded=True)

    # This is main thread. Will send status of each websocket every hour
    send_web_socket_updates()
    return "kind of worked"


@app.route("/holdings.json", methods=['GET'])
def holdings():
    kite = get_kite_client_from_cache()
    response = kite.holdings()
    if response:
        holding_list = []
        for holding in response:
            holding['arbitrage_quantity'] = None
            holding['authorisation'] = json.dumps(holding['authorisation'])
            holding_list.append(Holdings(**holding))
        add_all(holding_list)
    return jsonify(response)


@app.route("/margins.json", methods=['GET'])
def margins():
    kite = get_kite_client_from_cache()
    margin_resp = kite.margins()
    return jsonify(margin_resp)


@app.route("/instruments.json", methods=['GET'])
def instruments():
    kite = get_kite_client_from_cache()
    instrument_records = kite.instruments()
    instrument_model_list = instrument.convert_all(instrument_records)
    add_all(instrument_model_list)
    return jsonify(instrument_records)


if __name__ == "__main__":
    logging.info("Starting server: http://{host}:{port}".format(host=HOST, port=PORT))
    app.run(host=HOST, port=PORT, debug=True)
