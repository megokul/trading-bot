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
Fyers trading platform integration adapter for NSE/BSE/MCX markets.

This subpackage provides an instrument provider, data and execution clients,
configurations, data types and constants for connecting to and interacting with
Fyers' API.

Supported markets:
- NSE: National Stock Exchange (Equity, F&O, Currency)
- BSE: Bombay Stock Exchange (Equity)
- MCX: Multi Commodity Exchange (Commodities)

For convenience, the most commonly used symbols are re-exported at the
subpackage's top level, so downstream code can simply import from
``nautilus_trader.adapters.fyers``.

Example
-------
>>> from nautilus_trader.adapters.fyers import (
...     FYERS_VENUE,
...     FyersDataClientConfig,
...     FyersExecClientConfig,
...     FyersLiveDataClientFactory,
...     FyersLiveExecClientFactory,
... )

"""

from nautilus_trader.adapters.fyers.config import FyersDataClientConfig
from nautilus_trader.adapters.fyers.config import FyersExecClientConfig
from nautilus_trader.adapters.fyers.config import FyersInstrumentProviderConfig
from nautilus_trader.adapters.fyers.constants import FYERS
from nautilus_trader.adapters.fyers.constants import FYERS_CLIENT_ID
from nautilus_trader.adapters.fyers.constants import FYERS_VENUE
from nautilus_trader.adapters.fyers.data import FyersDataClient
from nautilus_trader.adapters.fyers.enums import FyersDataType
from nautilus_trader.adapters.fyers.enums import FyersExchange
from nautilus_trader.adapters.fyers.enums import FyersOrderSide
from nautilus_trader.adapters.fyers.enums import FyersOrderStatus
from nautilus_trader.adapters.fyers.enums import FyersOrderType
from nautilus_trader.adapters.fyers.enums import FyersProductType
from nautilus_trader.adapters.fyers.enums import FyersSegment
from nautilus_trader.adapters.fyers.enums import FyersValidity
from nautilus_trader.adapters.fyers.execution import FyersExecutionClient
from nautilus_trader.adapters.fyers.factories import FyersLiveDataClientFactory
from nautilus_trader.adapters.fyers.factories import FyersLiveExecClientFactory
from nautilus_trader.adapters.fyers.factories import get_cached_fyers_http_client
from nautilus_trader.adapters.fyers.factories import get_cached_fyers_instrument_provider
from nautilus_trader.adapters.fyers.providers import FyersInstrumentProvider
from nautilus_trader.adapters.fyers.symbol import FyersSymbol
from nautilus_trader.adapters.fyers.symbol import build_equity_symbol
from nautilus_trader.adapters.fyers.symbol import build_futures_symbol
from nautilus_trader.adapters.fyers.symbol import build_option_symbol
from nautilus_trader.adapters.fyers.symbol import parse_fyers_symbol
from nautilus_trader.adapters.fyers.symbol import to_fyers_symbol


__all__ = [
    # Constants
    "FYERS",
    "FYERS_CLIENT_ID",
    "FYERS_VENUE",
    # Configuration
    "FyersDataClientConfig",
    "FyersExecClientConfig",
    "FyersInstrumentProviderConfig",
    # Enums
    "FyersDataType",
    "FyersExchange",
    "FyersOrderSide",
    "FyersOrderStatus",
    "FyersOrderType",
    "FyersProductType",
    "FyersSegment",
    "FyersValidity",
    # Clients
    "FyersDataClient",
    "FyersExecutionClient",
    # Factories
    "FyersLiveDataClientFactory",
    "FyersLiveExecClientFactory",
    "get_cached_fyers_http_client",
    "get_cached_fyers_instrument_provider",
    # Providers
    "FyersInstrumentProvider",
    # Symbol utilities
    "FyersSymbol",
    "build_equity_symbol",
    "build_futures_symbol",
    "build_option_symbol",
    "parse_fyers_symbol",
    "to_fyers_symbol",
]
