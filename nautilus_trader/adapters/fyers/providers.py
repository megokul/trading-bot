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
Fyers instrument provider.
"""

import csv
import io
from typing import Any

from nautilus_trader.adapters.fyers.config import FyersInstrumentProviderConfig
from nautilus_trader.adapters.fyers.constants import FYERS_VENUE
from nautilus_trader.adapters.fyers.constants import SYMBOL_MASTER_BSE_CM
from nautilus_trader.adapters.fyers.constants import SYMBOL_MASTER_MCX_COM
from nautilus_trader.adapters.fyers.constants import SYMBOL_MASTER_NSE_CD
from nautilus_trader.adapters.fyers.constants import SYMBOL_MASTER_NSE_CM
from nautilus_trader.adapters.fyers.constants import SYMBOL_MASTER_NSE_FO
from nautilus_trader.adapters.fyers.enums import FyersInstrumentType
from nautilus_trader.adapters.fyers.symbol import get_instrument_type
from nautilus_trader.adapters.fyers.symbol import parse_futures_symbol
from nautilus_trader.adapters.fyers.symbol import parse_option_symbol
from nautilus_trader.common.component import Logger
from nautilus_trader.common.providers import InstrumentProvider
from nautilus_trader.core.nautilus_pyo3 import HttpClient
from nautilus_trader.core.nautilus_pyo3 import HttpMethod
from nautilus_trader.model.currencies import INR
from nautilus_trader.model.enums import AssetClass
from nautilus_trader.model.enums import OptionKind
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.identifiers import Symbol
from nautilus_trader.model.instruments import Equity
from nautilus_trader.model.instruments import FuturesContract
from nautilus_trader.model.instruments import Instrument
from nautilus_trader.model.instruments import OptionsContract
from nautilus_trader.model.objects import Price
from nautilus_trader.model.objects import Quantity


class FyersInstrumentProvider(InstrumentProvider):
    """
    Instrument provider for Fyers.

    Loads instruments from Fyers symbol master CSV files.

    Parameters
    ----------
    config : FyersInstrumentProviderConfig
        The provider configuration.
    logger : Logger, optional
        The logger instance.

    """

    def __init__(
        self,
        config: FyersInstrumentProviderConfig,
        logger: Logger | None = None,
    ) -> None:
        super().__init__()
        self._config = config
        self._logger = logger
        self._http_client: HttpClient | None = None

        # Segment URL mapping
        self._segment_urls = {
            "NSE_CM": SYMBOL_MASTER_NSE_CM,
            "NSE_FO": SYMBOL_MASTER_NSE_FO,
            "NSE_CD": SYMBOL_MASTER_NSE_CD,
            "BSE_CM": SYMBOL_MASTER_BSE_CM,
            "MCX_COM": SYMBOL_MASTER_MCX_COM,
        }

    async def load_all_async(
        self,
        filters: dict[str, Any] | None = None,
    ) -> None:
        """
        Load all instruments from configured segments.

        Parameters
        ----------
        filters : dict, optional
            Additional filters to apply.

        """
        self._http_client = HttpClient()

        try:
            for segment in self._config.segments:
                url = self._segment_urls.get(segment)
                if url:
                    await self._load_segment(segment, url, filters)

        finally:
            self._http_client = None

        if self._logger:
            self._logger.info(f"Loaded {len(self._instruments)} instruments")

    async def load_ids_async(
        self,
        instrument_ids: list[InstrumentId],
        filters: dict[str, Any] | None = None,
    ) -> None:
        """
        Load specific instruments by ID.

        Parameters
        ----------
        instrument_ids : list[InstrumentId]
            The instrument IDs to load.
        filters : dict, optional
            Additional filters to apply.

        """
        # Load all first, then filter
        await self.load_all_async(filters)

        # Keep only requested instruments
        requested_ids = set(instrument_ids)
        to_remove = [
            inst_id for inst_id in self._instruments
            if inst_id not in requested_ids
        ]
        for inst_id in to_remove:
            del self._instruments[inst_id]

    async def load_async(
        self,
        instrument_id: InstrumentId,
        filters: dict[str, Any] | None = None,
    ) -> None:
        """
        Load a specific instrument.

        Parameters
        ----------
        instrument_id : InstrumentId
            The instrument ID to load.
        filters : dict, optional
            Additional filters to apply.

        """
        await self.load_ids_async([instrument_id], filters)

    async def _load_segment(
        self,
        segment: str,
        url: str,
        filters: dict[str, Any] | None,
    ) -> None:
        """Load instruments from a symbol master CSV."""
        try:
            response = await self._http_client.request(
                method=HttpMethod.GET,
                url=url,
            )

            content = response.body.decode("utf-8")
            reader = csv.DictReader(io.StringIO(content))

            for row in reader:
                try:
                    instrument = self._parse_instrument(row, segment)
                    if instrument:
                        # Apply filters
                        if filters and not self._passes_filters(instrument, filters):
                            continue

                        self._instruments[instrument.id] = instrument
                        self.add(instrument)

                except Exception as e:
                    if self._logger:
                        self._logger.warning(f"Failed to parse instrument: {e}")
                    continue

        except Exception as e:
            if self._logger:
                self._logger.error(f"Failed to load segment {segment}: {e}")

    def _parse_instrument(
        self,
        row: dict[str, str],
        segment: str,
    ) -> Instrument | None:
        """Parse a CSV row to an Instrument."""
        # Get symbol - column name varies between files
        symbol = (
            row.get("symbol")
            or row.get("Symbol")
            or row.get("SYMBOL")
            or row.get("sym_ticker")
        )

        if not symbol:
            return None

        # Create instrument ID
        instrument_id = InstrumentId(Symbol(symbol), FYERS_VENUE)

        # Get common properties
        tick_size = float(row.get("tick_size", row.get("Tick Size", "0.05")))
        lot_size = int(row.get("lot_size", row.get("Lot Size", "1")))

        # Determine instrument type from symbol
        inst_type = get_instrument_type(symbol)

        # Create appropriate instrument type
        if inst_type == FyersInstrumentType.OPTION:
            return self._create_option(row, instrument_id, symbol, tick_size, lot_size)
        elif inst_type == FyersInstrumentType.FUTURE:
            return self._create_future(row, instrument_id, symbol, tick_size, lot_size)
        else:
            return self._create_equity(row, instrument_id, symbol, tick_size, lot_size)

    def _create_equity(
        self,
        row: dict[str, str],
        instrument_id: InstrumentId,
        symbol: str,
        tick_size: float,
        lot_size: int,
    ) -> Equity:
        """Create an Equity instrument."""
        return Equity(
            instrument_id=instrument_id,
            raw_symbol=Symbol(symbol),
            currency=INR,
            price_precision=2,
            price_increment=Price.from_str(f"{tick_size:.2f}"),
            lot_size=Quantity.from_int(lot_size),
            isin=row.get("isin", row.get("ISIN", "")),
            ts_event=0,
            ts_init=0,
        )

    def _create_future(
        self,
        row: dict[str, str],
        instrument_id: InstrumentId,
        symbol: str,
        tick_size: float,
        lot_size: int,
    ) -> FuturesContract | None:
        """Create a FuturesContract instrument."""
        parsed = parse_futures_symbol(symbol)
        if not parsed:
            return None

        # Get expiry date
        expiry_str = row.get("expiry", row.get("Expiry", ""))

        return FuturesContract(
            instrument_id=instrument_id,
            raw_symbol=Symbol(symbol),
            asset_class=AssetClass.INDEX,
            currency=INR,
            price_precision=2,
            price_increment=Price.from_str(f"{tick_size:.2f}"),
            multiplier=Quantity.from_int(lot_size),
            lot_size=Quantity.from_int(lot_size),
            underlying=parsed.underlying,
            activation_ns=0,
            expiration_ns=0,  # Would need to parse expiry_str
            ts_event=0,
            ts_init=0,
        )

    def _create_option(
        self,
        row: dict[str, str],
        instrument_id: InstrumentId,
        symbol: str,
        tick_size: float,
        lot_size: int,
    ) -> OptionsContract | None:
        """Create an OptionsContract instrument."""
        parsed = parse_option_symbol(symbol)
        if not parsed:
            return None

        from nautilus_trader.adapters.fyers.enums import FyersOptionType

        return OptionsContract(
            instrument_id=instrument_id,
            raw_symbol=Symbol(symbol),
            asset_class=AssetClass.INDEX,
            currency=INR,
            price_precision=2,
            price_increment=Price.from_str(f"{tick_size:.2f}"),
            multiplier=Quantity.from_int(lot_size),
            lot_size=Quantity.from_int(lot_size),
            underlying=parsed.underlying,
            kind=OptionKind.CALL if parsed.option_type == FyersOptionType.CALL else OptionKind.PUT,
            strike_price=Price.from_int(parsed.strike),
            activation_ns=0,
            expiration_ns=0,  # Would need to parse from row
            ts_event=0,
            ts_init=0,
        )

    def _passes_filters(
        self,
        instrument: Instrument,
        filters: dict[str, Any],
    ) -> bool:
        """Check if instrument passes filters."""
        # Exchange filter
        if "exchange" in filters:
            exchange = filters["exchange"]
            symbol = instrument.id.symbol.value
            if not symbol.startswith(f"{exchange}:"):
                return False

        # Underlying filter (for F&O)
        if "underlying" in filters:
            underlying = filters["underlying"]
            symbol = instrument.id.symbol.value
            if underlying not in symbol:
                return False

        # Instrument type filter
        if "instrument_type" in filters:
            inst_type = get_instrument_type(instrument.id.symbol.value)
            if inst_type != filters["instrument_type"]:
                return False

        return True
