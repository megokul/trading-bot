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
Fyers adapter constants.
"""

from nautilus_trader.model.identifiers import ClientId
from nautilus_trader.model.identifiers import Venue


# Venue identifiers
FYERS: str = "FYERS"
FYERS_VENUE: Venue = Venue(FYERS)
FYERS_CLIENT_ID: ClientId = ClientId(FYERS)

# API URLs
FYERS_HTTP_URL: str = "https://api-t1.fyers.in/api/v3"
FYERS_WS_URL: str = "wss://socket.fyers.in/hsm/v1"
FYERS_DATA_WS_URL: str = "wss://socket.fyers.in"

# Symbol master URLs for instrument data
SYMBOL_MASTER_NSE_CM: str = "https://public.fyers.in/sym_details/NSE_CM.csv"
SYMBOL_MASTER_NSE_FO: str = "https://public.fyers.in/sym_details/NSE_FO.csv"
SYMBOL_MASTER_BSE_CM: str = "https://public.fyers.in/sym_details/BSE_CM.csv"
SYMBOL_MASTER_MCX_COM: str = "https://public.fyers.in/sym_details/MCX_COM.csv"
SYMBOL_MASTER_NSE_CD: str = "https://public.fyers.in/sym_details/NSE_CD.csv"

# Rate limits
MAX_REQUESTS_PER_DAY: int = 100_000
MAX_ORDERS_PER_SECOND: int = 10

# Trading hours (IST)
MARKET_OPEN_TIME: str = "09:15"
MARKET_CLOSE_TIME: str = "15:30"
PRE_MARKET_OPEN: str = "09:00"
PRE_MARKET_CLOSE: str = "09:08"

# Token expiry (IST) - SEBI compliance requires daily token refresh
TOKEN_EXPIRY_TIME: str = "03:00"

# Lot sizes for indices
NIFTY_LOT_SIZE: int = 50
BANKNIFTY_LOT_SIZE: int = 15
FINNIFTY_LOT_SIZE: int = 40
MIDCPNIFTY_LOT_SIZE: int = 75

# Supported exchanges
SUPPORTED_EXCHANGES: list[str] = ["NSE", "BSE", "MCX"]

# Supported segments
SUPPORTED_SEGMENTS: list[str] = ["CM", "FO", "CD", "COM"]
