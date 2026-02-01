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
Fyers symbol parsing utilities.

Fyers symbol format:
- Equity: NSE:RELIANCE-EQ, BSE:RELIANCE-A
- Index: NSE:NIFTY50-INDEX, NSE:NIFTYBANK-INDEX
- Futures: NSE:NIFTY25JANFUT, NSE:SBIN25JANFUT
- Options: NSE:NIFTY25JAN23000CE, NSE:NIFTY25JAN22500PE
"""

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from nautilus_trader.adapters.fyers.constants import FYERS_VENUE
from nautilus_trader.adapters.fyers.enums import FyersExchange
from nautilus_trader.adapters.fyers.enums import FyersInstrumentType
from nautilus_trader.adapters.fyers.enums import FyersOptionType
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.identifiers import Symbol


if TYPE_CHECKING:
    pass


@dataclass
class FyersSymbol:
    """Parsed Fyers symbol components."""

    exchange: str
    symbol: str
    raw_symbol: str  # Original Fyers format

    @classmethod
    def from_fyers_string(cls, fyers_symbol: str) -> "FyersSymbol":
        """
        Parse a Fyers symbol string.

        Parameters
        ----------
        fyers_symbol : str
            The Fyers symbol string (e.g., "NSE:RELIANCE-EQ").

        Returns
        -------
        FyersSymbol

        """
        if ":" in fyers_symbol:
            exchange, symbol = fyers_symbol.split(":", 1)
        else:
            exchange = "NSE"  # Default to NSE
            symbol = fyers_symbol

        return cls(
            exchange=exchange,
            symbol=symbol,
            raw_symbol=fyers_symbol,
        )

    def to_instrument_id(self) -> InstrumentId:
        """Convert to NautilusTrader InstrumentId."""
        return InstrumentId(Symbol(self.symbol), FYERS_VENUE)

    def to_fyers_string(self) -> str:
        """Convert to Fyers symbol string format."""
        return f"{self.exchange}:{self.symbol}"


@dataclass
class FyersOptionSymbol:
    """Parsed Fyers option symbol components."""

    underlying: str
    expiry_year: str
    expiry_month: str
    strike: int
    option_type: FyersOptionType


@dataclass
class FyersFuturesSymbol:
    """Parsed Fyers futures symbol components."""

    underlying: str
    expiry_year: str
    expiry_month: str


def parse_fyers_symbol(fyers_symbol: str) -> InstrumentId:
    """
    Parse Fyers symbol to NautilusTrader InstrumentId.

    Parameters
    ----------
    fyers_symbol : str
        The Fyers symbol string (e.g., "NSE:RELIANCE-EQ").

    Returns
    -------
    InstrumentId

    Examples
    --------
    >>> parse_fyers_symbol("NSE:RELIANCE-EQ")
    InstrumentId("RELIANCE-EQ.FYERS")
    >>> parse_fyers_symbol("NSE:NIFTY25JAN23000CE")
    InstrumentId("NIFTY25JAN23000CE.FYERS")

    """
    return FyersSymbol.from_fyers_string(fyers_symbol).to_instrument_id()


def to_fyers_symbol(instrument_id: InstrumentId, exchange: str = "NSE") -> str:
    """
    Convert NautilusTrader InstrumentId to Fyers symbol format.

    Parameters
    ----------
    instrument_id : InstrumentId
        The NautilusTrader instrument ID.
    exchange : str, default "NSE"
        The exchange code.

    Returns
    -------
    str
        The Fyers symbol string.

    Examples
    --------
    >>> to_fyers_symbol(InstrumentId.from_str("RELIANCE-EQ.FYERS"))
    "NSE:RELIANCE-EQ"

    """
    symbol = instrument_id.symbol.value
    return f"{exchange}:{symbol}"


def parse_option_symbol(symbol: str) -> FyersOptionSymbol | None:
    """
    Parse option symbol to extract components.

    Parameters
    ----------
    symbol : str
        The option symbol (e.g., "NIFTY25JAN23000CE").

    Returns
    -------
    FyersOptionSymbol or None
        The parsed components, or None if not a valid option symbol.

    Examples
    --------
    >>> result = parse_option_symbol("NIFTY25JAN23000CE")
    >>> result.underlying
    "NIFTY"
    >>> result.strike
    23000
    >>> result.option_type
    FyersOptionType.CALL

    """
    # Pattern: UNDERLYING + YY + MMM + STRIKE + CE/PE
    # Examples: NIFTY25JAN23000CE, BANKNIFTY25JAN48000PE
    pattern = r"^([A-Z]+)(\d{2})([A-Z]{3})(\d+)(CE|PE)$"
    match = re.match(pattern, symbol)

    if match:
        return FyersOptionSymbol(
            underlying=match.group(1),
            expiry_year=match.group(2),
            expiry_month=match.group(3),
            strike=int(match.group(4)),
            option_type=FyersOptionType.CALL if match.group(5) == "CE" else FyersOptionType.PUT,
        )
    return None


def parse_futures_symbol(symbol: str) -> FyersFuturesSymbol | None:
    """
    Parse futures symbol to extract components.

    Parameters
    ----------
    symbol : str
        The futures symbol (e.g., "NIFTY25JANFUT").

    Returns
    -------
    FyersFuturesSymbol or None
        The parsed components, or None if not a valid futures symbol.

    Examples
    --------
    >>> result = parse_futures_symbol("NIFTY25JANFUT")
    >>> result.underlying
    "NIFTY"
    >>> result.expiry_month
    "JAN"

    """
    # Pattern: UNDERLYING + YY + MMM + FUT
    # Examples: NIFTY25JANFUT, SBIN25FEBFUT
    pattern = r"^([A-Z]+)(\d{2})([A-Z]{3})FUT$"
    match = re.match(pattern, symbol)

    if match:
        return FyersFuturesSymbol(
            underlying=match.group(1),
            expiry_year=match.group(2),
            expiry_month=match.group(3),
        )
    return None


def get_instrument_type(symbol: str) -> FyersInstrumentType:
    """
    Determine the instrument type from a Fyers symbol.

    Parameters
    ----------
    symbol : str
        The symbol string (without exchange prefix).

    Returns
    -------
    FyersInstrumentType

    """
    if symbol.endswith("-INDEX"):
        return FyersInstrumentType.INDEX
    elif symbol.endswith("CE") or symbol.endswith("PE"):
        if parse_option_symbol(symbol):
            return FyersInstrumentType.OPTION
    elif symbol.endswith("FUT"):
        if parse_futures_symbol(symbol):
            return FyersInstrumentType.FUTURE
    elif symbol.endswith("-EQ") or symbol.endswith("-A") or symbol.endswith("-B"):
        return FyersInstrumentType.EQUITY

    # Default to equity for unknown formats
    return FyersInstrumentType.EQUITY


def get_exchange_from_symbol(fyers_symbol: str) -> FyersExchange:
    """
    Extract the exchange from a Fyers symbol.

    Parameters
    ----------
    fyers_symbol : str
        The Fyers symbol string (e.g., "NSE:RELIANCE-EQ").

    Returns
    -------
    FyersExchange

    """
    if ":" in fyers_symbol:
        exchange_str = fyers_symbol.split(":")[0]
        try:
            return FyersExchange(exchange_str)
        except ValueError:
            return FyersExchange.NSE
    return FyersExchange.NSE


def build_equity_symbol(name: str, exchange: str = "NSE") -> str:
    """
    Build a Fyers equity symbol.

    Parameters
    ----------
    name : str
        The stock name (e.g., "RELIANCE").
    exchange : str, default "NSE"
        The exchange code.

    Returns
    -------
    str
        The Fyers symbol string.

    """
    suffix = "-EQ" if exchange == "NSE" else "-A"
    return f"{exchange}:{name}{suffix}"


def build_futures_symbol(
    underlying: str,
    expiry_year: str,
    expiry_month: str,
    exchange: str = "NSE",
) -> str:
    """
    Build a Fyers futures symbol.

    Parameters
    ----------
    underlying : str
        The underlying symbol (e.g., "NIFTY", "SBIN").
    expiry_year : str
        The expiry year (2 digits, e.g., "25").
    expiry_month : str
        The expiry month (3 letters, e.g., "JAN").
    exchange : str, default "NSE"
        The exchange code.

    Returns
    -------
    str
        The Fyers symbol string.

    """
    return f"{exchange}:{underlying}{expiry_year}{expiry_month}FUT"


def build_option_symbol(
    underlying: str,
    expiry_year: str,
    expiry_month: str,
    strike: int,
    option_type: FyersOptionType,
    exchange: str = "NSE",
) -> str:
    """
    Build a Fyers option symbol.

    Parameters
    ----------
    underlying : str
        The underlying symbol (e.g., "NIFTY", "BANKNIFTY").
    expiry_year : str
        The expiry year (2 digits, e.g., "25").
    expiry_month : str
        The expiry month (3 letters, e.g., "JAN").
    strike : int
        The strike price.
    option_type : FyersOptionType
        The option type (CALL or PUT).
    exchange : str, default "NSE"
        The exchange code.

    Returns
    -------
    str
        The Fyers symbol string.

    """
    return f"{exchange}:{underlying}{expiry_year}{expiry_month}{strike}{option_type.value}"
