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
Fyers adapter enums.
"""

from enum import Enum
from enum import IntEnum
from enum import unique


@unique
class FyersExchange(str, Enum):
    """Fyers supported exchanges."""

    NSE = "NSE"
    BSE = "BSE"
    MCX = "MCX"


@unique
class FyersSegment(str, Enum):
    """Fyers market segments."""

    CM = "CM"    # Cash/Capital Market (Equity)
    FO = "FO"    # Futures & Options
    CD = "CD"    # Currency Derivatives
    COM = "COM"  # Commodities


@unique
class FyersProductType(str, Enum):
    """Fyers product types for orders."""

    CNC = "CNC"          # Cash and Carry (delivery)
    INTRADAY = "INTRADAY"  # Intraday/MIS
    MARGIN = "MARGIN"    # Margin trading
    CO = "CO"            # Cover Order
    BO = "BO"            # Bracket Order


@unique
class FyersOrderType(IntEnum):
    """Fyers order types."""

    LIMIT = 1
    MARKET = 2
    STOP_LOSS_MARKET = 3  # SL-M (Stop Loss Market)
    STOP_LOSS_LIMIT = 4   # SL-L (Stop Loss Limit)


@unique
class FyersOrderSide(IntEnum):
    """Fyers order side."""

    BUY = 1
    SELL = -1


@unique
class FyersOrderStatus(IntEnum):
    """Fyers order status codes."""

    CANCELLED = 1
    TRADED = 2         # Fully filled
    TRANSIT = 3        # In transit to exchange
    REJECTED = 4
    PENDING = 5        # Waiting at exchange
    EXPIRED = 6
    PARTIALLY_FILLED = 7


@unique
class FyersValidity(str, Enum):
    """Fyers order validity/time in force."""

    DAY = "DAY"  # Valid for the day
    IOC = "IOC"  # Immediate or Cancel


@unique
class FyersPositionSide(IntEnum):
    """Fyers position side."""

    LONG = 1
    SHORT = -1
    FLAT = 0


@unique
class FyersResolution(str, Enum):
    """Fyers historical data resolution."""

    MINUTE_1 = "1"
    MINUTE_2 = "2"
    MINUTE_3 = "3"
    MINUTE_5 = "5"
    MINUTE_10 = "10"
    MINUTE_15 = "15"
    MINUTE_20 = "20"
    MINUTE_30 = "30"
    MINUTE_60 = "60"
    MINUTE_120 = "120"
    MINUTE_240 = "240"
    DAY = "D"
    WEEK = "W"
    MONTH = "M"


@unique
class FyersDataType(str, Enum):
    """Fyers WebSocket data subscription types."""

    LTP = "ltp"          # Last Traded Price only
    QUOTE = "quote"      # Quote data (bid/ask)
    DEPTH = "depth"      # Full market depth (L2)


@unique
class FyersOrderSource(str, Enum):
    """Fyers order source."""

    WEB = "W"
    MOBILE = "M"
    API = "A"
    ADMIN = "R"


@unique
class FyersMarketStatus(IntEnum):
    """Fyers market status codes."""

    CLOSED = 0
    OPEN = 1
    PRE_OPEN = 2
    POST_CLOSE = 3


@unique
class FyersInstrumentType(IntEnum):
    """Fyers instrument type codes."""

    EQUITY = 0
    FUTURE = 1
    OPTION = 2
    INDEX = 3
    CURRENCY = 4
    COMMODITY = 5


@unique
class FyersOptionType(str, Enum):
    """Fyers option type."""

    CALL = "CE"
    PUT = "PE"
