# -------------------------------------------------------------------------------------------------
#  Copyright (C) 2015-2026 Nautech Systems Pty Ltd. All rights reserved.
#  https://nautechsystems.io
#
#  Licensed under the GNU Lesser General Public License Version 3.0 (the "License");
#  You may not use this file except in compliance with the License.
#  You may obtain a copy of the License at https://www.gnu.org/licenses/lgpl-3.0.en.html
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
# -------------------------------------------------------------------------------------------------
"""
Fyers adapter configuration classes.
"""

from nautilus_trader.adapters.fyers.constants import FYERS_VENUE
from nautilus_trader.adapters.fyers.enums import FyersProductType
from nautilus_trader.config import InstrumentProviderConfig
from nautilus_trader.config import LiveDataClientConfig
from nautilus_trader.config import LiveExecClientConfig
from nautilus_trader.config import PositiveInt
from nautilus_trader.model.identifiers import Venue


class FyersInstrumentProviderConfig(InstrumentProviderConfig, frozen=True):
    """
    Configuration for ``FyersInstrumentProvider`` instances.

    Parameters
    ----------
    load_all : bool, default False
        If all venue instruments should be loaded on start.
    load_ids : frozenset[InstrumentId], optional
        The list of instrument IDs to be loaded on start (if `load_all` is False).
    filters : frozendict or dict[str, Any], optional
        The venue specific instrument loading filters to apply.
    filter_callable: str, optional
        A fully qualified path to a callable that takes a single argument, `instrument` and returns a bool.
    log_warnings : bool, default True
        If parser warnings should be logged.
    segments : list[str], default ["NSE_CM", "NSE_FO"]
        The market segments to load instruments from.
        Options: NSE_CM, NSE_FO, NSE_CD, BSE_CM, MCX_COM

    """

    segments: list[str] = ["NSE_CM", "NSE_FO"]


class FyersDataClientConfig(LiveDataClientConfig, frozen=True):
    """
    Configuration for ``FyersDataClient`` instances.

    Parameters
    ----------
    venue : Venue, default FYERS_VENUE
        The venue for the client.
    client_id : str
        The Fyers App ID (e.g., "XXXXXX-100").
    access_token : str
        The Fyers OAuth access token.
    base_url_http : str, optional
        The HTTP client custom endpoint override.
    base_url_ws : str, optional
        The WebSocket client custom endpoint override.
    update_instruments_interval_mins : PositiveInt or None, default 60
        The interval (minutes) between reloading instruments from the venue.
    ws_heartbeat_interval_secs : PositiveInt, default 30
        The WebSocket heartbeat interval in seconds.
    ws_reconnect_delay_secs : PositiveInt, default 5
        The delay in seconds before attempting WebSocket reconnection.
    ws_max_reconnect_attempts : PositiveInt, default 10
        The maximum number of WebSocket reconnection attempts.

    """

    venue: Venue = FYERS_VENUE
    client_id: str | None = None
    access_token: str | None = None
    base_url_http: str | None = None
    base_url_ws: str | None = None
    update_instruments_interval_mins: PositiveInt | None = 60
    ws_heartbeat_interval_secs: PositiveInt = 30
    ws_reconnect_delay_secs: PositiveInt = 5
    ws_max_reconnect_attempts: PositiveInt = 10


class FyersExecClientConfig(LiveExecClientConfig, frozen=True):
    """
    Configuration for ``FyersExecutionClient`` instances.

    Parameters
    ----------
    venue : Venue, default FYERS_VENUE
        The venue for the client.
    client_id : str
        The Fyers App ID (e.g., "XXXXXX-100").
    access_token : str
        The Fyers OAuth access token.
    base_url_http : str, optional
        The HTTP client custom endpoint override.
    default_product_type : FyersProductType, default INTRADAY
        The default product type for orders.
        Options: CNC (delivery), INTRADAY (MIS), MARGIN, CO, BO
    max_order_rate : PositiveInt, default 10
        The maximum order submission rate per second.
    recv_window_ms : PositiveInt, default 5000
        The receive window (milliseconds) for HTTP requests.
    max_retries : PositiveInt or None, optional
        The maximum number of times an order request will be retried.
    retry_delay_initial_ms : PositiveInt or None, optional
        The initial delay (milliseconds) between retries.
    retry_delay_max_ms : PositiveInt or None, optional
        The maximum delay (milliseconds) between retries.

    """

    venue: Venue = FYERS_VENUE
    client_id: str | None = None
    access_token: str | None = None
    base_url_http: str | None = None
    default_product_type: FyersProductType = FyersProductType.INTRADAY
    max_order_rate: PositiveInt = 10
    recv_window_ms: PositiveInt = 5_000
    max_retries: PositiveInt | None = None
    retry_delay_initial_ms: PositiveInt | None = None
    retry_delay_max_ms: PositiveInt | None = None
