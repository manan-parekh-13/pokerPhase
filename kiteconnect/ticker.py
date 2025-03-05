# -*- coding: utf-8 -*-
"""
    ticker.py

    Websocket implementation for kite ticker

    :copyright: (c) 2021 by Zerodha Technology Pvt. Ltd.
    :license: see LICENSE for details.
"""
import six
import sys
import time
import json
import logging
from datetime import datetime
from twisted.internet import reactor, ssl
from twisted.python import log as twisted_log
from twisted.internet.protocol import ReconnectingClientFactory
from autobahn.twisted.websocket import WebSocketClientProtocol, \
    WebSocketClientFactory, connectWS
import threading
from .__version__ import __version__, __title__
from .global_stuff import get_executor_by_process_id
from .utils import get_env_variable, convert_date_time_to_us, resolve_ipv6
from twisted.internet.abstract import isIPv6Address

useCython = get_env_variable("USE_CYTHON_FUNC")
if useCython == "yes":
    from cython.cython_functions_c import _parse_binary
else:
    from .utils import _parse_binary

log = logging.getLogger(__name__)
current_process_id = 0


class KiteTickerClientProtocol(WebSocketClientProtocol):
    """Kite ticker autobahn WebSocket protocol."""

    PING_INTERVAL = 1
    KEEPALIVE_INTERVAL = 5

    _next_ping = None
    _next_pong_check = None
    _last_pong_time = None
    _last_ping_time = None

    process_id = None

    def __init__(self, *args, **kwargs):
        """Initialize protocol with all options passed from factory."""
        global current_process_id
        self.process_id = current_process_id
        if current_process_id == 0:
            current_process_id = 1
        else:
            current_process_id = 0
        super(KiteTickerClientProtocol, self).__init__(*args, **kwargs)

    # Overide method
    def onConnect(self, response):  # noqa
        """Called when WebSocket server connection was established"""
        self.factory.ws = self

        if self.factory.on_connect:
            self.factory.on_connect(self, response)

        # Reset reconnect on successful reconnect
        self.factory.resetDelay()

    # Overide method
    def onOpen(self):  # noqa
        """Called when the initial WebSocket opening handshake was completed."""
        # send ping
        self._loop_ping()
        # init last pong check after X seconds
        self._loop_pong_check()

        if self.factory.on_open:
            self.factory.on_open(self)

    # Overide method
    def onMessage(self, payload, is_binary):  # noqa
        """Called when text or binary message is received."""
        if self.factory.on_message:
            self.factory.on_message(self, payload, is_binary, convert_date_time_to_us(datetime.now()))

    # Overide method
    def onClose(self, was_clean, code, reason):  # noqa
        """Called when connection is closed."""
        if not was_clean:
            if self.factory.on_error:
                self.factory.on_error(self, code, reason)

        if self.factory.on_close:
            self.factory.on_close(self, code, reason)

        # Cancel next ping and timer
        self._last_ping_time = None
        self._last_pong_time = None

        if self._next_ping:
            self._next_ping.cancel()

        if self._next_pong_check:
            self._next_pong_check.cancel()

    def onPong(self, response):  # noqa
        """Called when pong message is received."""
        if self._last_pong_time and self.factory.debug:
            log.debug("last pong was {} seconds back.".format(time.time() - self._last_pong_time))

        self._last_pong_time = time.time()

        if self.factory.debug:
            log.debug("pong => {}".format(response))

    """
    Custom helper and exposed methods.
    """

    def _loop_ping(self):  # noqa
        """Start a ping loop where it sends ping message every X seconds."""
        if self.factory.debug:
            if self._last_ping_time:
                log.debug("last ping was {} seconds back.".format(time.time() - self._last_ping_time))

        # Set current time as last ping time
        self._last_ping_time = time.time()

        # Call self after X seconds
        self._next_ping = self.factory.reactor.callLater(self.PING_INTERVAL, self._loop_ping)

    def _loop_pong_check(self):
        """
        Timer sortof to check if connection is still there.

        Checks last pong message time and disconnects the existing connection to make sure it doesn't become a ghost connection.
        """
        if self._last_pong_time:
            # No pong message since long time, so init reconnect
            last_pong_diff = time.time() - self._last_pong_time
            if last_pong_diff > (2 * self.PING_INTERVAL):
                if self.factory.debug:
                    log.debug("Last pong was {} seconds ago. So dropping connection to reconnect.".format(
                        last_pong_diff))
                # drop existing connection to avoid ghost connection
                self.dropConnection(abort=True)

        # Call self after X seconds
        self._next_pong_check = self.factory.reactor.callLater(self.PING_INTERVAL, self._loop_pong_check)


class KiteTickerClientFactory(WebSocketClientFactory, ReconnectingClientFactory):
    """Autobahn WebSocket client factory to implement reconnection and custom callbacks."""

    protocol = KiteTickerClientProtocol
    maxDelay = 5
    maxRetries = 10

    _last_connection_time = None

    def __init__(self, *args, **kwargs):
        """Initialize with default callback method values."""
        self.debug = False
        self.ws = None
        self.on_open = None
        self.on_error = None
        self.on_close = None
        self.on_message = None
        self.on_connect = None
        self.on_reconnect = None
        self.on_noreconnect = None

        super(KiteTickerClientFactory, self).__init__(*args, **kwargs)

        logging.info(json.dumps(self.protocol, indent=4))
        host = self.protocol.host
        if not isIPv6Address(host):
            resolved_ipv6 = resolve_ipv6(host)
            if resolved_ipv6:
                self.protocol.host = resolved_ipv6
            else:
                raise Exception(f"Could not resolve IPv6 address for {host}")

    def startedConnecting(self, connector):  # noqa
        """On connecting start or reconnection."""
        if not self._last_connection_time and self.debug:
            log.debug("Start WebSocket connection.")

        self._last_connection_time = time.time()

    def clientConnectionFailed(self, connector, reason):  # noqa
        """On connection failure (When connect request fails)"""
        if self.retries > 0:
            log.error("Retrying connection. Retry attempt count: {}. Next retry in around: {} seconds".format(self.retries, int(round(self.delay))))

            # on reconnect callback
            if self.on_reconnect:
                self.on_reconnect(self.retries)

        # Retry the connection
        self.retry(connector)
        self.send_noreconnect()

    def clientConnectionLost(self, connector, reason):  # noqa
        """On connection lost (When ongoing connection got disconnected)."""
        if self.retries > 0:
            # on reconnect callback
            if self.on_reconnect:
                self.on_reconnect(self.retries)

        # Retry the connection
        self.retry(connector)
        self.send_noreconnect()

    def send_noreconnect(self):
        """Callback `no_reconnect` if max retries are exhausted."""
        if self.maxRetries is not None and (self.retries > self.maxRetries):
            if self.debug:
                log.debug("Maximum retries ({}) exhausted.".format(self.maxRetries))
                # Stop the loop for exceeding max retry attempts
                self.stop()

            if self.on_noreconnect:
                self.on_noreconnect()


class KiteTicker(object):
    """
    The WebSocket client for connecting to Kite Connect's streaming quotes service.

    Getting started:
    ---------------
        #!python
        import logging
        from kiteconnect import KiteTicker

        logging.basicConfig(level=logging.DEBUG)

        # Initialise
        kws = KiteTicker("your_api_key", "your_access_token")

        def on_ticks(ws, ticks):
            # Callback to receive ticks.
            logging.debug("Ticks: {}".format(ticks))

        def on_connect(ws, response):
            # Callback on successful connect.
            # Subscribe to a list of instrument_tokens (RELIANCE and ACC here).
            ws.subscribe([738561, 5633])

            # Set RELIANCE to tick in `full` mode.
            ws.set_mode(ws.MODE_FULL, [738561])

        def on_close(ws, code, reason):
            # On connection close stop the event loop.
            # Reconnection will not happen after executing `ws.stop()`
            ws.stop()

        # Assign the callbacks.
        kws.on_ticks = on_ticks
        kws.on_connect = on_connect
        kws.on_close = on_close

        # Infinite loop on the main thread. Nothing after this will run.
        # You have to use the pre-defined callbacks to manage subscriptions.
        kws.connect()

    Callbacks
    ---------
    In below examples `ws` is the currently initialised WebSocket object.

    - `on_ticks(ws, ticks)` -  Triggered when ticks are recevied.
        - `ticks` - List of `tick` object. Check below for sample structure.
    - `on_close(ws, code, reason)` -  Triggered when connection is closed.
        - `code` - WebSocket standard close event code (https://developer.mozilla.org/en-US/docs/Web/API/CloseEvent)
        - `reason` - DOMString indicating the reason the server closed the connection
    - `on_error(ws, code, reason)` -  Triggered when connection is closed with an error.
        - `code` - WebSocket standard close event code (https://developer.mozilla.org/en-US/docs/Web/API/CloseEvent)
        - `reason` - DOMString indicating the reason the server closed the connection
    - `on_connect` -  Triggered when connection is established successfully.
        - `response` - Response received from server on successful connection.
    - `on_message(ws, payload, is_binary, ticker_received_time)` -  Triggered when message is received from the server.
        - `payload` - Raw response from the server (either text or binary).
        - `is_binary` - Bool to check if response is binary type.
    - `on_reconnect(ws, attempts_count)` -  Triggered when auto reconnection is attempted.
        - `attempts_count` - Current reconnect attempt number.
    - `on_noreconnect(ws)` -  Triggered when number of auto reconnection attempts exceeds `reconnect_tries`.
    - `on_order_update(ws, data)` -  Triggered when there is an order update for the connected user.


    Tick structure (passed to the `on_ticks` callback)
    ---------------------------
        [{
            'instrument_token': 53490439,
            'mode': 'full',
            'volume_traded': 12510,
            'last_price': 4084.0,
            'average_traded_price': 4086.55,
            'last_traded_quantity': 1,
            'total_buy_quantity': 2356
            'total_sell_quantity': 2440,
            'change': 0.46740467404674046,
            'last_trade_time': datetime.datetime(2018, 1, 15, 13, 16, 54),
            'exchange_timestamp': datetime.datetime(2018, 1, 15, 13, 16, 56),
            'oi': 21845,
            'oi_day_low': 0,
            'oi_day_high': 0,
            'ohlc': {
                'high': 4093.0,
                'close': 4065.0,
                'open': 4088.0,
                'low': 4080.0
            },
            'tradable': True,
            'depth': {
                'sell': [{
                    'price': 4085.0,
                    'orders': 1048576,
                    'quantity': 43
                }, {
                    'price': 4086.0,
                    'orders': 2752512,
                    'quantity': 134
                }, {
                    'price': 4087.0,
                    'orders': 1703936,
                    'quantity': 133
                }, {
                    'price': 4088.0,
                    'orders': 1376256,
                    'quantity': 70
                }, {
                    'price': 4089.0,
                    'orders': 1048576,
                    'quantity': 46
                }],
                'buy': [{
                    'price': 4084.0,
                    'orders': 589824,
                    'quantity': 53
                }, {
                    'price': 4083.0,
                    'orders': 1245184,
                    'quantity': 145
                }, {
                    'price': 4082.0,
                    'orders': 1114112,
                    'quantity': 63
                }, {
                    'price': 4081.0,
                    'orders': 1835008,
                    'quantity': 69
                }, {
                    'price': 4080.0,
                    'orders': 2752512,
                    'quantity': 89
                }]
            }
        },
        ...,
        ...]

    Auto reconnection
    -----------------

    Auto reconnection is enabled by default and it can be disabled by passing `reconnect` param while initialising `KiteTicker`.
    On a side note, reconnection mechanism cannot happen if event loop is terminated using `stop` method inside `on_close` callback.

    Auto reonnection mechanism is based on [Exponential backoff](https://en.wikipedia.org/wiki/Exponential_backoff) algorithm in which
    next retry interval will be increased exponentially. `reconnect_max_delay` and `reconnect_max_tries` params can be used to tewak
    the alogrithm where `reconnect_max_delay` is the maximum delay after which subsequent reconnection interval will become constant and
    `reconnect_max_tries` is maximum number of retries before its quiting reconnection.

    For example if `reconnect_max_delay` is 60 seconds and `reconnect_max_tries` is 50 then the first reconnection interval starts from
    minimum interval which is 2 seconds and keep increasing up to 60 seconds after which it becomes constant and when reconnection attempt
    is reached upto 50 then it stops reconnecting.

    method `stop_retry` can be used to stop ongoing reconnect attempts and `on_reconnect` callback will be called with current reconnect
    attempt and `on_noreconnect` is called when reconnection attempts reaches max retries.
    """

    EXCHANGE_MAP = {
        "nse": 1,
        "nfo": 2,
        "cds": 3,
        "bse": 4,
        "bfo": 5,
        "bcd": 6,
        "mcx": 7,
        "mcxsx": 8,
        "indices": 9,
        # bsecds is replaced with it's official segment name bcd
        # so,bsecds key will be depreciated in next version
        "bsecds": 6,
    }

    # Default connection timeout
    CONNECT_TIMEOUT = 30
    # Default Reconnect max delay.
    RECONNECT_MAX_DELAY = 60
    # Default reconnect attempts
    RECONNECT_MAX_TRIES = 50
    # Default root API endpoint. It's possible to
    # override this by passing the `root` parameter during initialisation.
    ROOT_URI = "wss://[2606:4700:9642:3edd:964:486:6812:7428]:443"

    # Available streaming modes.
    MODE_FULL = "full"
    MODE_QUOTE = "quote"
    MODE_LTP = "ltp"

    # Flag to set if its first connect
    _is_first_connect = True

    # Available actions.
    _message_code = 11
    _message_subscribe = "subscribe"
    _message_unsubscribe = "unsubscribe"
    _message_setmode = "mode"

    # Minimum delay which should be set between retries. User can't set less than this
    _minimum_reconnect_max_delay = 5
    # Maximum number or retries user can set
    _maximum_reconnect_max_tries = 300

    def __init__(self, enc_token, debug=False, root=None,
                 reconnect=True, reconnect_max_tries=RECONNECT_MAX_TRIES, reconnect_max_delay=RECONNECT_MAX_DELAY,
                 connect_timeout=CONNECT_TIMEOUT, token_map={}, ws_id=None, mode=MODE_FULL, try_ordering=False,
                 trading_symbol_map={}):
        """
        Initialise websocket client instance.

        - `api_key` is the API key issued to you
        - `access_token` is the token obtained after the login flow in
            exchange for the `request_token`. Pre-login, this will default to None,
            but once you have obtained it, you should
            persist it in a database or session to pass
            to the Kite Connect class initialisation for subsequent requests.
        - `root` is the websocket API end point root. Unless you explicitly
            want to send API requests to a non-default endpoint, this
            can be ignored.
        - `reconnect` is a boolean to enable WebSocket autreconnect in case of network failure/disconnection.
        - `reconnect_max_delay` in seconds is the maximum delay after which subsequent reconnection interval will become constant. Defaults to 60s and minimum acceptable value is 5s.
        - `reconnect_max_tries` is maximum number reconnection attempts. Defaults to 50 attempts and maximum up to 300 attempts.
        - `connect_timeout` in seconds is the maximum interval after which connection is considered as timeout. Defaults to 30s.
        """
        self.root = root or self.ROOT_URI

        # Set max reconnect tries
        if reconnect_max_tries > self._maximum_reconnect_max_tries:
            log.warning("`reconnect_max_tries` can not be more than {val}. Setting to highest possible value - {val}.".format(
                val=self._maximum_reconnect_max_tries))
            self.reconnect_max_tries = self._maximum_reconnect_max_tries
        else:
            self.reconnect_max_tries = reconnect_max_tries

        # Set max reconnect delay
        if reconnect_max_delay < self._minimum_reconnect_max_delay:
            log.warning("`reconnect_max_delay` can not be less than {val}. Setting to lowest possible value - {val}.".format(
                val=self._minimum_reconnect_max_delay))
            self.reconnect_max_delay = self._minimum_reconnect_max_delay
        else:
            self.reconnect_max_delay = reconnect_max_delay

        self.connect_timeout = connect_timeout

        self.socket_url = "{root}?enctoken={enc_token}".format(
                root=self.root,
                enc_token=enc_token
            )

        # Debug enables logs
        self.debug = debug

        # Initialize default value for websocket object
        self.ws = None

        # Placeholders for callbacks.
        self.on_ticks = None
        self.on_open = None
        self.on_close = None
        self.on_error = None
        self.on_connect = None
        self.on_message = None
        self.on_reconnect = None
        self.on_noreconnect = None

        # Text message updates
        self.on_order_update = None

        # List of current subscribed tokens
        self.subscribed_tokens = {}

        # Dict of instrument_token to arbitrage_instrument
        self.token_map = token_map

        # Dict of trading symbol to true
        self.trading_symbol_map = trading_symbol_map

        self.ws_id = ws_id

        self.mode = mode

        self.try_ordering = try_ordering

        self.reactor_thread = None

    def _create_connection(self, url, **kwargs):
        """Create a WebSocket client connection."""
        self.factory = KiteTickerClientFactory(url, **kwargs)

        # Alias for current websocket connection
        self.ws = self.factory.ws

        self.factory.debug = self.debug

        # Register private callbacks
        self.factory.on_open = self._on_open
        self.factory.on_error = self._on_error
        self.factory.on_close = self._on_close
        self.factory.on_message = self._on_message
        self.factory.on_connect = self._on_connect
        self.factory.on_reconnect = self._on_reconnect
        self.factory.on_noreconnect = self._on_noreconnect

        self.factory.maxDelay = self.reconnect_max_delay
        self.factory.maxRetries = self.reconnect_max_tries

    def _user_agent(self):
        return (__title__ + "-python/").capitalize() + __version__

    def connect(self, threaded=False, disable_ssl_verification=False, proxy=None):
        """
        Establish a websocket connection.

        - `threaded` is a boolean indicating if the websocket client has to be run in threaded mode or not
        - `disable_ssl_verification` disables building ssl context
        - `proxy` is a dictionary with keys `host` and `port` which denotes the proxy settings
        """
        # Custom headers
        headers = {
            "X-Kite-Version": "3",  # For version 3
        }

        # Init WebSocket client factory
        self._create_connection(self.socket_url,
                                useragent=self._user_agent(),
                                proxy=proxy, headers=headers)

        # Set SSL context
        context_factory = None
        if self.factory.isSecure and not disable_ssl_verification:
            context_factory = ssl.ClientContextFactory()

        # Establish WebSocket connection to a server
        connectWS(self.factory, contextFactory=context_factory, timeout=self.connect_timeout)

        if self.debug:
            twisted_log.startLogging(sys.stdout)

        # Run in seperate thread of blocking
        opts = {}

        # Run when reactor is not running
        if not reactor.running:
            if threaded:
                # Signals are not allowed in non-main thread by twisted so suppress it.
                opts["installSignalHandlers"] = False
                self.reactor_thread = threading.Thread(target=reactor.run, kwargs=opts)
                self.reactor_thread.daemon = True
                self.reactor_thread.start()
                logging.debug("reactor_thread {}".format(self.reactor_thread.name))
            else:
                reactor.run(**opts)

    def is_connected(self):
        """Check if WebSocket connection is established."""
        if self.ws and self.ws.state == self.ws.STATE_OPEN:
            return True
        else:
            return False

    def _close(self, code=None, reason=None):
        """Close the WebSocket connection."""
        if self.ws:
            self.ws.sendClose(code, reason)

    def close(self, code=None, reason=None):
        """Close the WebSocket connection."""
        self.stop_retry()
        self._close(code, reason)

    def stop(self):
        """Stop the event loop. Should be used if main thread has to be closed in `on_close` method.
        Reconnection mechanism cannot happen past this method
        """
        reactor.stop()

    def stop_retry(self):
        """Stop auto retry when it is in progress."""
        if self.factory:
            self.factory.stopTrying()

    def subscribe(self, instrument_tokens):
        """
        Subscribe to a list of instrument_tokens.

        - `instrument_tokens` is list of instrument instrument_tokens to subscribe
        """
        try:
            self.ws.sendMessage(
                six.b(json.dumps({"a": self._message_subscribe, "v": instrument_tokens}))
            )

            for token in instrument_tokens:
                self.subscribed_tokens[token] = self.MODE_QUOTE

            return True
        except Exception as e:
            self._close(reason="Error while subscribe: {}".format(str(e)))
            raise

    def unsubscribe(self, instrument_tokens):
        """
        Unsubscribe the given list of instrument_tokens.

        - `instrument_tokens` is list of instrument_tokens to unsubscribe.
        """
        try:
            self.ws.sendMessage(
                six.b(json.dumps({"a": self._message_unsubscribe, "v": instrument_tokens}))
            )

            for token in instrument_tokens:
                try:
                    del (self.subscribed_tokens[token])
                except KeyError:
                    pass

            return True
        except Exception as e:
            self._close(reason="Error while unsubscribe: {}".format(str(e)))
            raise

    def set_mode(self, mode, instrument_tokens):
        """
        Set streaming mode for the given list of tokens.

        - `mode` is the mode to set. It can be one of the following class constants:
            MODE_LTP, MODE_QUOTE, or MODE_FULL.
        - `instrument_tokens` is list of instrument tokens on which the mode should be applied
        """
        try:
            self.ws.sendMessage(
                six.b(json.dumps({"a": self._message_setmode, "v": [mode, instrument_tokens]}))
            )

            # Update modes
            for token in instrument_tokens:
                self.subscribed_tokens[token] = mode

            return True
        except Exception as e:
            self._close(reason="Error while setting mode: {}".format(str(e)))
            raise

    def resubscribe(self):
        """Resubscribe to all current subscribed tokens."""
        modes = {}

        for token in self.subscribed_tokens:
            m = self.subscribed_tokens[token]

            if not modes.get(m):
                modes[m] = []

            modes[m].append(token)

        for mode in modes:
            if self.debug:
                log.debug("Resubscribe and set mode: {} - {}".format(mode, modes[mode]))

            self.subscribe(modes[mode])
            self.set_mode(mode, modes[mode])

    def _on_connect(self, ws, response):
        self.ws = ws
        if self.on_connect:
            self.on_connect(self, response)

    def _on_close(self, ws, code, reason):
        """Call `on_close` callback when connection is closed."""
        log.error("Connection closed: {} - {}".format(code, str(reason)))

        if self.on_close:
            self.on_close(self, code, reason)

    def _on_error(self, ws, code, reason):
        """Call `on_error` callback when connection throws an error."""
        log.error("Connection error: {} - {}".format(code, str(reason)))

        if self.on_error:
            self.on_error(self, code, reason)

    def _on_message(self, ws, payload, is_binary, ticker_received_time):
        # If the message is binary, parse it and send it to the callback.
        executor = get_executor_by_process_id(ws.process_id)
        if self.on_ticks and is_binary and len(payload) > 4:
            executor.submit(self.on_ticks(self, _parse_binary(self, payload, ticker_received_time)))

        # Parse text messages
        if not is_binary:
            executor.submit(self._parse_text_message, payload)

        """Call `on_message` callback when text message is received."""
        if self.on_message:
            self.on_message(self, payload, is_binary)

    def _on_open(self, ws):
        # Resubscribe if its reconnect
        if not self._is_first_connect:
            self.resubscribe()

        # Set first connect to false once its connected first time
        self._is_first_connect = False

        if self.on_open:
            return self.on_open(self)

    def _on_reconnect(self, attempts_count):
        if self.on_reconnect:
            return self.on_reconnect(self, attempts_count)

    def _on_noreconnect(self):
        if self.on_noreconnect:
            return self.on_noreconnect(self)

    def _parse_text_message(self, payload):
        """Parse text message."""
        # Decode unicode data
        if not six.PY2 and type(payload) == bytes:
            payload = payload.decode("utf-8")

        try:
            data = json.loads(payload)
        except ValueError:
            return

        # Order update callback
        if (self.on_order_update
                and data
                and data.get("type") == "order"
                and data.get('tradingsymbol') in self.trading_symbol_map):
            self.on_order_update(self, data)

        # Custom error with websocket error code 0
        if data.get("type") == "error":
            self._on_error(self, 0, data)

