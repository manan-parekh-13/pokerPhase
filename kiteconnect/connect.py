# -*- coding: utf-8 -*-
"""
    connect.py

    API wrapper for Kite Connect REST APIs.

    :copyright: (c) 2021 by Zerodha Technology.
    :license: see LICENSE for details.
"""
from six import StringIO, PY2
from six.moves.urllib.parse import urljoin
import csv
import json
import dateutil.parser
import logging
import datetime
import requests
import warnings
import time
import threading

from .__version__ import __version__, __title__
from kiteconnect.utils import get_env_variable, convert_str_to_datetime, truncate_microseconds
import kiteconnect.exceptions as ex

log = logging.getLogger(__name__)


class KiteConnect(object):
    """
    The Kite Connect API wrapper class.

    In production, you may initialise a single instance of this class per `api_key`.
    """

    # Default root API endpoint. It's possible to
    # override this by passing the `root` parameter during initialisation.
    _default_root_uri = "https://kite.zerodha.com"
    _default_timeout = 7  # In seconds

    # Kite connect header version
    kite_header_version = "3"

    # Constants
    # Products
    PRODUCT_MIS = "MIS"
    PRODUCT_MIS_INT = 1
    PRODUCT_CNC = "CNC"
    PRODUCT_CNC_INT = 2
    PRODUCT_NRML = "NRML"
    PRODUCT_NRML_INT = 3
    PRODUCT_CO = "CO"
    PRODUCT_CO_INT = 4

    # Order types
    ORDER_TYPE_MARKET = "MARKET"
    ORDER_TYPE_LIMIT = "LIMIT"
    ORDER_TYPE_SLM = "SL-M"
    ORDER_TYPE_SL = "SL"

    # Varities
    VARIETY_REGULAR = "regular"
    VARIETY_CO = "co"
    VARIETY_AMO = "amo"
    VARIETY_ICEBERG = "iceberg"
    VARIETY_AUCTION = "auction"

    # Transaction type
    TRANSACTION_TYPE_BUY = "BUY"
    TRANSACTION_TYPE_BUY_INT = 1
    TRANSACTION_TYPE_SELL = "SELL"
    TRANSACTION_TYPE_SELL_INT = 2

    # Validity
    VALIDITY_DAY = "DAY"
    VALIDITY_IOC = "IOC"
    VALIDITY_TTL = "TTL"

    # Position Type
    POSITION_TYPE_DAY = "day"
    POSITION_TYPE_OVERNIGHT = "overnight"

    # Exchanges
    EXCHANGE_NSE = "NSE"
    EXCHANGE_BSE = "BSE"
    EXCHANGE_NFO = "NFO"
    EXCHANGE_CDS = "CDS"
    EXCHANGE_BFO = "BFO"
    EXCHANGE_MCX = "MCX"
    EXCHANGE_BCD = "BCD"

    # Margins segments
    MARGIN_EQUITY = "equity"
    MARGIN_COMMODITY = "commodity"

    # Order status (subset of opportunity status lifecycle)
    REJECTED = "REJECTED"  # STATUS_REJECTED
    CANCELLED = "CANCELLED"  # STATUS_CANCELLED
    COMPLETE = "COMPLETE"  # STATUS_COMPLETE

    # GTT order type
    GTT_TYPE_OCO = "two-leg"
    GTT_TYPE_SINGLE = "single"

    # GTT order status
    GTT_STATUS_ACTIVE = "active"
    GTT_STATUS_TRIGGERED = "triggered"
    GTT_STATUS_DISABLED = "disabled"
    GTT_STATUS_EXPIRED = "expired"
    GTT_STATUS_CANCELLED = "cancelled"
    GTT_STATUS_REJECTED = "rejected"
    GTT_STATUS_DELETED = "deleted"

    # URIs to various calls
    _routes = {
        # ------------------------------------- TESTED -----------------------------------------------------------
        "login.requestId": "/api/login",
        "generate.otp": "/oms/trusted/kitefront/user/{user_id}/twofa/generate_otp",
        "verify.otp": "/api/twofa",

        "user.margins": "/oms/user/margins",
        "user.margins.segment": "/oms/user/margins/{segment}",

        "orders": "/oms/orders",
        "order.info": "/oms/orders/{order_id}",
        "order.place": "/oms/orders/{variety}",

        "portfolio.holdings": "/oms/portfolio/holdings",
        "portfolio.holdings.auction": "/oms/portfolio/holdings/auctions",
        "portfolio.positions": "/oms/portfolio/positions",

        "market.instruments.all": "/instruments",

        # --------------------------------------------------- HISTORICAL ----------------------------------------
        "market.quote": "/oms/quote",
        "market.historical": "/oms/instruments/historical/{instrument_token}/{interval}",


        # -------------------------------------------------- UNTESTED -------------------------------------------
        # "api.token": "/session/token",
        # "api.token.invalidate": "/session/token",
        # "api.token.renew": "/session/refresh_token",
        # "user.profile": "/user/profile",
        #
        # "trades": "/trades",
        #
        # "order.modify": "/orders/{variety}/{order_id}",
        # "order.cancel": "/orders/{variety}/{order_id}",
        # "order.trades": "/orders/{order_id}/trades",
        #
        # "portfolio.positions.convert": "/portfolio/positions",
        #
        # # MF api endpoints
        # "mf.orders": "/mf/orders",
        # "mf.order.info": "/mf/orders/{order_id}",
        # "mf.order.place": "/mf/orders",
        # "mf.order.cancel": "/mf/orders/{order_id}",
        #
        # "mf.sips": "/mf/sips",
        # "mf.sip.info": "/mf/sips/{sip_id}",
        # "mf.sip.place": "/mf/sips",
        # "mf.sip.modify": "/mf/sips/{sip_id}",
        # "mf.sip.cancel": "/mf/sips/{sip_id}",
        #
        # "mf.holdings": "/mf/holdings",
        # "mf.instruments": "/mf/instruments",
        #
        # "market.instruments": "/instruments/{exchange}",
        # "market.margins": "/margins/{segment}",
        # "market.trigger_range": "/instruments/trigger_range/{transaction_type}",

        # "market.quote.ohlc": "/quote/ohlc",
        # "market.quote.ltp": "/quote/ltp",
        #
        # # GTT endpoints
        # "gtt": "/gtt/triggers",
        # "gtt.place": "/gtt/triggers",
        # "gtt.info": "/gtt/triggers/{trigger_id}",
        # "gtt.modify": "/gtt/triggers/{trigger_id}",
        # "gtt.delete": "/gtt/triggers/{trigger_id}",
        #
        # # Margin computation endpoints
        # "order.margins": "/margins/orders",
        # "order.margins.basket": "/margins/basket",
        # "order.contract_note": "/charges/orders",
    }

    def __init__(self,
                 enc_token=None,
                 root=None,
                 debug=False,
                 timeout=None,
                 proxies=None,
                 pool=None,
                 disable_ssl=False,
                 user_id=None,
                 password=None,
                 request_id=None,
                 open_positions=None):
        """
        Initialise a new Kite Connect client instance.

        - `api_key` is the key issued to you
        - `access_token` is the token obtained after the login flow in
            exchange for the `request_token` . Pre-login, this will default to None,
        but once you have obtained it, you should
        persist it in a database or session to pass
        to the Kite Connect class initialisation for subsequent requests.
        - `root` is the API end point root. Unless you explicitly
        want to send API requests to a non-default endpoint, this
        can be ignored.
        - `debug`, if set to True, will serialise and print requests
        and responses to stdout.
        - `timeout` is the time (seconds) for which the API client will wait for
        a request to complete before it fails. Defaults to 7 seconds
        - `proxies` to set requests proxy.
        Check [python requests documentation](http://docs.python-requests.org/en/master/user/advanced/#proxies) for usage and examples.
        - `pool` is manages request pools. It takes a dict of params accepted by HTTPAdapter as described here in [python requests documentation](http://docs.python-requests.org/en/master/api/#requests.adapters.HTTPAdapter)
        - `disable_ssl` disables the SSL verification while making a request.
        If set requests won't throw SSLError if its set to custom `root` url without SSL.
        """
        self.debug = debug
        self.session_expiry_hook = None
        self.disable_ssl = disable_ssl
        self.enc_token = enc_token
        self.proxies = proxies if proxies else {}

        self.user_id = user_id
        self.password = password
        self.request_id = request_id

        self.root = root or self._default_root_uri
        self.timeout = timeout or self._default_timeout

        self.lock = threading.Lock()

        self.open_positions = open_positions

        # Create requests session by default
        # Same session to be used by pool connections
        self.reqsession = requests.Session()
        if pool:
            reqadapter = requests.adapters.HTTPAdapter(**pool)
            self.reqsession.mount("https://", reqadapter)

        # disable requests SSL warning
        requests.packages.urllib3.disable_warnings()

    def expire_current_enc_token(self):
        self.set_enc_token(None)

    def set_enc_token(self, enc_token):
        """Set the `enc_token` received after a successful authentication."""
        self.enc_token = enc_token

    @staticmethod
    def get_latest_otp_from_mail():
        gmail_api_key = get_env_variable('GMAIL_API_KEY')
        gmail_api_path = get_env_variable('GMAIL_API_PATH')

        params = {
            "label": "zerodha-otp",
            "passkey": gmail_api_key
        }

        response = requests.get(gmail_api_path, params=params)

        if response.status_code == 200:
            meta_obj = json.loads(response.text)
            if not meta_obj:
                return None
            meta_obj["timestamp"] = convert_str_to_datetime(meta_obj["timestamp"])
            print("Response content:", meta_obj)
            return meta_obj
        else:
            print("GET request failed with status code:", response.status_code)

    def return_latest_otp_later_than(self, given_timestamp, max_attempts=3, wait_time=5):
        attempts = 0
        given_timestamp = truncate_microseconds(given_timestamp)

        while attempts < max_attempts:
            attempts += 1
            otp_meta = self.get_latest_otp_from_mail()
            if not otp_meta:
                continue
            otp = otp_meta["otp"]
            timestamp = truncate_microseconds(otp_meta["timestamp"])

            if timestamp >= given_timestamp:
                return otp

            if attempts < max_attempts:
                print(
                    f"Latest OTP timestamp ({timestamp}) is not later than the given timestamp ({given_timestamp}). Retrying in {wait_time} seconds...")
                time.sleep(wait_time)

        return None

    def get_open_positions_by_trading_symbol_and_exchange(self, trading_symbol, exchange):
        with self.lock:
            return self.open_positions.get(f"{exchange}_{trading_symbol}") or 0

    def set_open_positions_by_symbol_and_exchange(self, new_positions, trading_symbol, exchange):
        with self.lock:
            self.open_positions[f"{exchange}_{trading_symbol}"] = new_positions

    def set_open_positions(self, new_positions_map):
        with self.lock:
            self.open_positions = new_positions_map

    def set_request_id(self, request_id):
        """Set the `request_id` received after a creating a login request."""
        self.request_id = request_id

    def generate_request_id(self):
        """
        Generate request_id for two-factor authentication using user id and password
        """
        resp = self._post("login.requestId", params={
            "user_id": self.user_id,
            "password": self.password,
        })
        if "request_id" in resp:
            self.set_request_id(resp["request_id"])

    def generate_otp_for_login_request(self):
        self._post("generate.otp", url_args={"user_id": self.user_id}, params={
            "request_id": self.request_id,
            "twofa_type": "sms"
        })

    def verify_otp_for_request_id(self, otp):
        self._post("verify.otp", params={
            "user_id": self.user_id,
            "request_id": self.request_id,
            "twofa_value": otp,
            "twofa_type": "sms"
        })

    def margins(self, segment=None):
        """Get account balance and cash margin details for a particular segment.

        - `segment` is the trading segment (eg: equity or commodity)
        """
        if segment:
            return self._get("user.margins.segment", url_args={"segment": segment})
        else:
            return self._get("user.margins")

    def profile(self):
        """Get user profile details."""
        return self._get("user.profile")

    # orders
    def place_order(self,
                    variety,
                    exchange,
                    tradingsymbol,
                    transaction_type,
                    quantity,
                    product,
                    order_type,
                    price=None,
                    validity=None,
                    validity_ttl=None,
                    disclosed_quantity=None,
                    trigger_price=None,
                    iceberg_legs=None,
                    iceberg_quantity=None,
                    auction_number=None,
                    tag=None):
        """Place an order."""
        params = locals()
        del (params["self"])

        for k in list(params.keys()):
            if params[k] is None:
                del (params[k])

        return self._post("order.place",
                          url_args={"variety": variety},
                          params=params)["order_id"]

    def modify_order(self,
                     variety,
                     order_id,
                     parent_order_id=None,
                     quantity=None,
                     price=None,
                     order_type=None,
                     trigger_price=None,
                     validity=None,
                     disclosed_quantity=None):
        """Modify an open order."""
        params = locals()
        del (params["self"])

        for k in list(params.keys()):
            if params[k] is None:
                del (params[k])

        return self._put("order.modify",
                         url_args={"variety": variety, "order_id": order_id},
                         params=params)["order_id"]

    def cancel_order(self, variety, order_id, parent_order_id=None):
        """Cancel an order."""
        return self._delete("order.cancel",
                            url_args={"variety": variety, "order_id": order_id},
                            params={"parent_order_id": parent_order_id})["order_id"]

    def exit_order(self, variety, order_id, parent_order_id=None):
        """Exit a CO order."""
        return self.cancel_order(variety, order_id, parent_order_id=parent_order_id)

    @staticmethod
    def _format_response(data):
        """Parse and format responses."""

        if type(data) == list:
            _list = data
        elif type(data) == dict:
            _list = [data]

        for item in _list:
            # Convert date time string to datetime object
            for field in ["order_timestamp", "exchange_timestamp", "created", "last_instalment", "fill_timestamp", "timestamp", "last_trade_time"]:
                if item.get(field) and len(item[field]) == 19:
                    item[field] = dateutil.parser.parse(item[field])

        return _list[0] if type(data) == dict else _list

    # orderbook and tradebook
    def orders(self):
        """Get list of orders."""
        return self._format_response(self._get("orders"))

    def order_history(self, order_id):
        """
        Get history of individual order.

        - `order_id` is the ID of the order to retrieve order history.
        """
        return self._format_response(self._get("order.info", url_args={"order_id": order_id}))

    def trades(self):
        """
        Retrieve the list of trades executed (all or ones under a particular order).

        An order can be executed in tranches based on market conditions.
        These trades are individually recorded under an order.
        """
        return self._format_response(self._get("trades"))

    def order_trades(self, order_id):
        """
        Retrieve the list of trades executed for a particular order.

        - `order_id` is the ID of the order to retrieve trade history.
        """
        return self._format_response(self._get("order.trades", url_args={"order_id": order_id}))

    def positions(self):
        """Retrieve the list of positions."""
        return self._get("portfolio.positions")

    def holdings(self):
        """Retrieve the list of equity holdings."""
        return self._get("portfolio.holdings")

    def get_auction_instruments(self):
        """ Retrieves list of available instruments for a auction session """
        return self._get("portfolio.holdings.auction")

    def convert_position(self,
                         exchange,
                         tradingsymbol,
                         transaction_type,
                         position_type,
                         quantity,
                         old_product,
                         new_product):
        """Modify an open position's product type."""
        return self._put("portfolio.positions.convert", params={
            "exchange": exchange,
            "tradingsymbol": tradingsymbol,
            "transaction_type": transaction_type,
            "position_type": position_type,
            "quantity": quantity,
            "old_product": old_product,
            "new_product": new_product
        })

    def mf_orders(self, order_id=None):
        """Get all mutual fund orders or individual order info."""
        if order_id:
            return self._format_response(self._get("mf.order.info", url_args={"order_id": order_id}))
        else:
            return self._format_response(self._get("mf.orders"))

    def place_mf_order(self,
                       tradingsymbol,
                       transaction_type,
                       quantity=None,
                       amount=None,
                       tag=None):
        """Place a mutual fund order."""
        return self._post("mf.order.place", params={
            "tradingsymbol": tradingsymbol,
            "transaction_type": transaction_type,
            "quantity": quantity,
            "amount": amount,
            "tag": tag
        })

    def cancel_mf_order(self, order_id):
        """Cancel a mutual fund order."""
        return self._delete("mf.order.cancel", url_args={"order_id": order_id})

    def mf_sips(self, sip_id=None):
        """Get list of all mutual fund SIP's or individual SIP info."""
        if sip_id:
            return self._format_response(self._get("mf.sip.info", url_args={"sip_id": sip_id}))
        else:
            return self._format_response(self._get("mf.sips"))

    def place_mf_sip(self,
                     tradingsymbol,
                     amount,
                     instalments,
                     frequency,
                     initial_amount=None,
                     instalment_day=None,
                     tag=None):
        """Place a mutual fund SIP."""
        return self._post("mf.sip.place", params={
            "tradingsymbol": tradingsymbol,
            "amount": amount,
            "initial_amount": initial_amount,
            "instalments": instalments,
            "frequency": frequency,
            "instalment_day": instalment_day,
            "tag": tag
        })

    def modify_mf_sip(self,
                      sip_id,
                      amount=None,
                      status=None,
                      instalments=None,
                      frequency=None,
                      instalment_day=None):
        """Modify a mutual fund SIP."""
        return self._put("mf.sip.modify",
                         url_args={"sip_id": sip_id},
                         params={
                             "amount": amount,
                             "status": status,
                             "instalments": instalments,
                             "frequency": frequency,
                             "instalment_day": instalment_day
                         })

    def cancel_mf_sip(self, sip_id):
        """Cancel a mutual fund SIP."""
        return self._delete("mf.sip.cancel", url_args={"sip_id": sip_id})

    def mf_holdings(self):
        """Get list of mutual fund holdings."""
        return self._get("mf.holdings")

    def mf_instruments(self):
        """Get list of mutual fund instruments."""
        return self._parse_mf_instruments(self._get("mf.instruments"))

    def instruments(self, exchange=None):
        """
        Retrieve the list of market instruments available to trade.

        Note that the results could be large, several hundred KBs in size,
        with tens of thousands of entries in the list.

        - `exchange` is specific exchange to fetch (Optional)
        """
        if exchange:
            return self._parse_instruments(self._get("market.instruments", url_args={"exchange": exchange}))
        else:
            return self._parse_instruments(self._get("market.instruments.all"))

    def quote(self, *instruments):
        """
        Retrieve quote for list of instruments.

        - `instruments` is a list of instruments, Instrument are in the format of `exchange:tradingsymbol`. For example NSE:INFY
        """
        ins = list(instruments)

        # If first element is a list then accept it as instruments list for legacy reason
        if len(instruments) > 0 and type(instruments[0]) == list:
            ins = instruments[0]

        data = self._get("market.quote", params={"i": ins})
        return {key: self._format_response(data[key]) for key in data}

    def ohlc(self, *instruments):
        """
        Retrieve OHLC and market depth for list of instruments.

        - `instruments` is a list of instruments, Instrument are in the format of `exchange:tradingsymbol`. For example NSE:INFY
        """
        ins = list(instruments)

        # If first element is a list then accept it as instruments list for legacy reason
        if len(instruments) > 0 and type(instruments[0]) == list:
            ins = instruments[0]

        return self._get("market.quote.ohlc", params={"i": ins})

    def ltp(self, *instruments):
        """
        Retrieve last price for list of instruments.

        - `instruments` is a list of instruments, Instrument are in the format of `exchange:tradingsymbol`. For example NSE:INFY
        """
        ins = list(instruments)

        # If first element is a list then accept it as instruments list for legacy reason
        if len(instruments) > 0 and type(instruments[0]) == list:
            ins = instruments[0]

        return self._get("market.quote.ltp", params={"i": ins})

    def historical_data(self, instrument_token, from_date, to_date, interval, continuous=False, oi=False):
        """
        Retrieve historical data (candles) for an instrument.

        Although the actual response JSON from the API does not have field
        names such has 'open', 'high' etc., this function call structures
        the data into an array of objects with field names. For example:

        - `instrument_token` is the instrument identifier (retrieved from the instruments()) call.
        - `from_date` is the From date (datetime object or string in format of yyyy-mm-dd HH:MM:SS.
        - `to_date` is the To date (datetime object or string in format of yyyy-mm-dd HH:MM:SS).
        - `interval` is the candle interval (minute, day, 5 minute etc.).
        - `continuous` is a boolean flag to get continuous data for futures and options instruments.
        - `oi` is a boolean flag to get open interest.
        """
        date_string_format = "%Y-%m-%d %H:%M:%S"
        from_date_string = from_date.strftime(date_string_format) if type(from_date) == datetime.datetime else from_date
        to_date_string = to_date.strftime(date_string_format) if type(to_date) == datetime.datetime else to_date

        data = self._get("market.historical",
                         url_args={"instrument_token": instrument_token, "interval": interval},
                         params={
                             "from": from_date_string,
                             "to": to_date_string,
                             "interval": interval,
                             "continuous": 1 if continuous else 0,
                             "oi": 1 if oi else 0
                         })

        return self._format_historical(data)

    @staticmethod
    def _format_historical(data):
        records = []
        for d in data["candles"]:
            record = {
                "date": dateutil.parser.parse(d[0]),
                "open": d[1],
                "high": d[2],
                "low": d[3],
                "close": d[4],
                "volume": d[5],
            }
            if len(d) == 7:
                record["oi"] = d[6]
            records.append(record)

        return records

    def trigger_range(self, transaction_type, *instruments):
        """Retrieve the buy/sell trigger range for Cover Orders."""
        ins = list(instruments)

        # If first element is a list then accept it as instruments list for legacy reason
        if len(instruments) > 0 and type(instruments[0]) == list:
            ins = instruments[0]

        return self._get("market.trigger_range",
                         url_args={"transaction_type": transaction_type.lower()},
                         params={"i": ins})

    def get_gtts(self):
        """Fetch list of gtt existing in an account"""
        return self._get("gtt")

    def get_gtt(self, trigger_id):
        """Fetch details of a GTT"""
        return self._get("gtt.info", url_args={"trigger_id": trigger_id})

    def _get_gtt_payload(self, trigger_type, tradingsymbol, exchange, trigger_values, last_price, orders):
        """Get GTT payload"""
        if type(trigger_values) != list:
            raise ex.InputException("invalid type for `trigger_values`")
        if trigger_type == self.GTT_TYPE_SINGLE and len(trigger_values) != 1:
            raise ex.InputException("invalid `trigger_values` for single leg order type")
        elif trigger_type == self.GTT_TYPE_OCO and len(trigger_values) != 2:
            raise ex.InputException("invalid `trigger_values` for OCO order type")

        condition = {
            "exchange": exchange,
            "tradingsymbol": tradingsymbol,
            "trigger_values": trigger_values,
            "last_price": last_price,
        }

        gtt_orders = []
        for o in orders:
            # Assert required keys inside gtt order.
            for req in ["transaction_type", "quantity", "order_type", "product", "price"]:
                if req not in o:
                    raise ex.InputException("`{req}` missing inside orders".format(req=req))
            gtt_orders.append({
                "exchange": exchange,
                "tradingsymbol": tradingsymbol,
                "transaction_type": o["transaction_type"],
                "quantity": int(o["quantity"]),
                "order_type": o["order_type"],
                "product": o["product"],
                "price": float(o["price"]),
            })

        return condition, gtt_orders

    def place_gtt(
        self, trigger_type, tradingsymbol, exchange, trigger_values, last_price, orders
    ):
        """
        Place GTT order

        - `trigger_type` The type of GTT order(single/two-leg).
        - `tradingsymbol` Trading symbol of the instrument.
        - `exchange` Name of the exchange.
        - `trigger_values` Trigger values (json array).
        - `last_price` Last price of the instrument at the time of order placement.
        - `orders` JSON order array containing following fields
            - `transaction_type` BUY or SELL
            - `quantity` Quantity to transact
            - `price` The min or max price to execute the order at (for LIMIT orders)
        """
        # Validations.
        assert trigger_type in [self.GTT_TYPE_OCO, self.GTT_TYPE_SINGLE]
        condition, gtt_orders = self._get_gtt_payload(trigger_type, tradingsymbol, exchange, trigger_values, last_price, orders)

        return self._post("gtt.place", params={
            "condition": json.dumps(condition),
            "orders": json.dumps(gtt_orders),
            "type": trigger_type})

    def modify_gtt(
        self, trigger_id, trigger_type, tradingsymbol, exchange, trigger_values, last_price, orders
    ):
        """
        Modify GTT order

        - `trigger_type` The type of GTT order(single/two-leg).
        - `tradingsymbol` Trading symbol of the instrument.
        - `exchange` Name of the exchange.
        - `trigger_values` Trigger values (json array).
        - `last_price` Last price of the instrument at the time of order placement.
        - `orders` JSON order array containing following fields
            - `transaction_type` BUY or SELL
            - `quantity` Quantity to transact
            - `price` The min or max price to execute the order at (for LIMIT orders)
        """
        condition, gtt_orders = self._get_gtt_payload(trigger_type, tradingsymbol, exchange, trigger_values, last_price, orders)

        return self._put("gtt.modify",
                         url_args={"trigger_id": trigger_id},
                         params={
                             "condition": json.dumps(condition),
                             "orders": json.dumps(gtt_orders),
                             "type": trigger_type})

    def delete_gtt(self, trigger_id):
        """Delete a GTT order."""
        return self._delete("gtt.delete", url_args={"trigger_id": trigger_id})

    def order_margins(self, params):
        """
        Calculate margins for requested order list considering the existing positions and open orders

        - `params` is list of orders to retrive margins detail
        """
        return self._post("order.margins", params=params, is_json=True)

    def basket_order_margins(self, params, consider_positions=True, mode=None):
        """
        Calculate total margins required for basket of orders including margin benefits

        - `params` is list of orders to fetch basket margin
        - `consider_positions` is a boolean to consider users positions
        - `mode` is margin response mode type. compact - Compact mode will only give the total margins
        """
        return self._post("order.margins.basket",
                          params=params,
                          is_json=True,
                          query_params={'consider_positions': consider_positions, 'mode': mode})

    def get_virtual_contract_note(self, params):
        """
        Calculates detailed charges order-wise for the order book
        - `params` is list of orders to fetch charges detail
        """
        return self._post("order.contract_note",
                          params=params,
                          is_json=True)

    @staticmethod
    def _warn(message):
        """ Add deprecation warning message """
        warnings.simplefilter('always', DeprecationWarning)
        warnings.warn(message, DeprecationWarning)

    @staticmethod
    def _parse_instruments(data):
        # decode to string for Python 3
        d = data
        # Decode unicode data
        if not PY2 and type(d) == bytes:
            d = data.decode("utf-8").strip()

        records = []
        reader = csv.DictReader(StringIO(d))

        for row in reader:
            row["instrument_token"] = int(row["instrument_token"])
            row["last_price"] = float(row["last_price"])
            row["strike"] = float(row["strike"])
            row["tick_size"] = float(row["tick_size"])
            row["lot_size"] = int(row["lot_size"])

            # Parse date
            if len(row["expiry"]) == 10:
                row["expiry"] = dateutil.parser.parse(row["expiry"]).date()

            records.append(row)

        return records

    @staticmethod
    def _parse_mf_instruments(data):
        # decode to string for Python 3
        d = data
        if not PY2 and type(d) == bytes:
            d = data.decode("utf-8").strip()

        records = []
        reader = csv.DictReader(StringIO(d))

        for row in reader:
            row["minimum_purchase_amount"] = float(row["minimum_purchase_amount"])
            row["purchase_amount_multiplier"] = float(row["purchase_amount_multiplier"])
            row["minimum_additional_purchase_amount"] = float(row["minimum_additional_purchase_amount"])
            row["minimum_redemption_quantity"] = float(row["minimum_redemption_quantity"])
            row["redemption_quantity_multiplier"] = float(row["redemption_quantity_multiplier"])
            row["purchase_allowed"] = bool(int(row["purchase_allowed"]))
            row["redemption_allowed"] = bool(int(row["redemption_allowed"]))
            row["last_price"] = float(row["last_price"])

            # Parse date
            if len(row["last_price_date"]) == 10:
                row["last_price_date"] = dateutil.parser.parse(row["last_price_date"]).date()

            records.append(row)

        return records

    @staticmethod
    def _user_agent():
        return (__title__ + "-python/").capitalize() + __version__

    def _get(self, route, url_args=None, params=None, is_json=False):
        """Alias for sending a GET request."""
        return self._request(route, "GET", url_args=url_args, params=params, is_json=is_json)

    def _post(self, route, url_args=None, params=None, is_json=False, query_params=None):
        """Alias for sending a POST request."""
        return self._request(route, "POST", url_args=url_args, params=params, is_json=is_json, query_params=query_params)

    def _put(self, route, url_args=None, params=None, is_json=False, query_params=None):
        """Alias for sending a PUT request."""
        return self._request(route, "PUT", url_args=url_args, params=params, is_json=is_json, query_params=query_params)

    def _delete(self, route, url_args=None, params=None, is_json=False):
        """Alias for sending a DELETE request."""
        return self._request(route, "DELETE", url_args=url_args, params=params, is_json=is_json)

    def _request(self, route, method, url_args=None, params=None, is_json=False, query_params=None):
        """Make an HTTP request."""
        # Form a restful URL
        if url_args:
            uri = self._routes[route].format(**url_args)
        else:
            uri = self._routes[route]

        url = urljoin(self.root, uri)

        # Custom headers
        headers = {
            "X-Kite-Version": self.kite_header_version,
            "User-Agent": self._user_agent()
        }

        if self.enc_token:
            # set authorization header
            auth_header = self.enc_token
            headers["authorization"] = "enctoken {}".format(auth_header)

        if self.debug:
            log.debug("Request: {method} {url} {params} {headers}".format(method=method, url=url, params=params, headers=headers))

        # prepare url query params
        if method in ["GET", "DELETE"]:
            query_params = params

        try:
            r = self.reqsession.request(method,
                                        url,
                                        json=params if (method in ["POST", "PUT"] and is_json) else None,
                                        data=params if (method in ["POST", "PUT"] and not is_json) else None,
                                        params=query_params,
                                        headers=headers,
                                        verify=not self.disable_ssl,
                                        allow_redirects=True,
                                        timeout=self.timeout,
                                        proxies=self.proxies)
        # Any requests lib related exceptions are raised here - https://requests.readthedocs.io/en/latest/api/#exceptions
        except Exception as e:
            raise e

        if self.debug:
            log.debug("Response: {code} {content}".format(code=r.status_code, content=r.content))

        # Validate the content type.
        if "json" in r.headers["content-type"]:
            try:
                data = r.json()
            except ValueError:
                raise ex.DataException("Couldn't parse the JSON response received from the server: {content}".format(
                    content=r.content))

            # api error
            if data.get("status") == "error" or data.get("error_type"):
                # Call session hook if its registered and TokenException is raised
                if r.status_code == 403 and data["error_type"] == "TokenException":
                    self.expire_current_enc_token()

                # native Kite errors
                exp = getattr(ex, data.get("error_type"), ex.GeneralException)
                raise exp(data["message"], code=r.status_code)

            # set enc_token from cookies if cookies exist and enc_token is not present
            if r.cookies and not self.enc_token:
                enctoken = r.cookies.get("enctoken")
                if enctoken:
                    self.set_enc_token(enctoken)

            return data["data"]
        elif "csv" in r.headers["content-type"]:
            return r.content
        else:
            raise ex.DataException("Unknown Content-Type ({content_type}) with response: ({content})".format(
                content_type=r.headers["content-type"],
                content=r.content))
