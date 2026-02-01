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
Fyers live market data client.
"""

import asyncio
from typing import Any

from nautilus_trader.adapters.fyers.config import FyersDataClientConfig
from nautilus_trader.adapters.fyers.constants import FYERS_VENUE
from nautilus_trader.adapters.fyers.enums import FyersDataType
from nautilus_trader.adapters.fyers.enums import FyersResolution
from nautilus_trader.adapters.fyers.http.client import FyersHttpClient
from nautilus_trader.adapters.fyers.parsing import parse_bar
from nautilus_trader.adapters.fyers.parsing import parse_quote_tick
from nautilus_trader.adapters.fyers.parsing import parse_trade_tick
from nautilus_trader.adapters.fyers.providers import FyersInstrumentProvider
from nautilus_trader.adapters.fyers.symbol import parse_fyers_symbol
from nautilus_trader.adapters.fyers.symbol import to_fyers_symbol
from nautilus_trader.adapters.fyers.websocket.client import FyersWebSocketClient
from nautilus_trader.cache.cache import Cache
from nautilus_trader.common.component import LiveClock
from nautilus_trader.common.component import MessageBus
from nautilus_trader.core.correctness import PyCondition
from nautilus_trader.live.data_client import LiveMarketDataClient
from nautilus_trader.model.data import Bar
from nautilus_trader.model.data import BarType
from nautilus_trader.model.data import DataType
from nautilus_trader.model.data import QuoteTick
from nautilus_trader.model.data import TradeTick
from nautilus_trader.model.identifiers import ClientId
from nautilus_trader.model.identifiers import InstrumentId


class FyersDataClient(LiveMarketDataClient):
    """
    Live market data client for Fyers.

    Parameters
    ----------
    loop : asyncio.AbstractEventLoop
        The event loop.
    client_id : ClientId
        The client ID.
    msgbus : MessageBus
        The message bus.
    cache : Cache
        The cache.
    clock : LiveClock
        The clock.
    instrument_provider : FyersInstrumentProvider
        The instrument provider.
    config : FyersDataClientConfig
        The client configuration.

    """

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        client_id: ClientId,
        msgbus: MessageBus,
        cache: Cache,
        clock: LiveClock,
        instrument_provider: FyersInstrumentProvider,
        config: FyersDataClientConfig,
    ) -> None:
        super().__init__(
            loop=loop,
            client_id=client_id,
            venue=FYERS_VENUE,
            msgbus=msgbus,
            cache=cache,
            clock=clock,
            instrument_provider=instrument_provider,
        )

        PyCondition.not_none(config.client_id, "config.client_id")
        PyCondition.not_none(config.access_token, "config.access_token")

        self._config = config

        # HTTP client for REST API
        self._http_client = FyersHttpClient(
            client_id=config.client_id,
            access_token=config.access_token,
            base_url=config.base_url_http,
            logger=self._log,
        )

        # WebSocket client for real-time data
        self._ws_client: FyersWebSocketClient | None = None

        # Subscription tracking
        self._subscribed_quotes: set[InstrumentId] = set()
        self._subscribed_trades: set[InstrumentId] = set()
        self._subscribed_bars: dict[BarType, InstrumentId] = {}

        # Symbol mapping (Fyers symbol -> InstrumentId)
        self._symbol_map: dict[str, InstrumentId] = {}

    async def _connect(self) -> None:
        """Connect to Fyers."""
        self._log.info("Connecting to Fyers...")

        # Connect HTTP client
        await self._http_client.connect()

        # Initialize WebSocket client
        self._ws_client = FyersWebSocketClient(
            client_id=self._config.client_id,
            access_token=self._config.access_token,
            on_message=self._handle_ws_message,
            on_error=self._handle_ws_error,
            ws_url=self._config.base_url_ws,
            logger=self._log,
            heartbeat_interval=self._config.ws_heartbeat_interval_secs,
            reconnect_delay=self._config.ws_reconnect_delay_secs,
            max_reconnect_attempts=self._config.ws_max_reconnect_attempts,
        )
        await self._ws_client.connect()

        # Load instruments
        await self._instrument_provider.load_all_async()

        self._log.info("Connected to Fyers")

    async def _disconnect(self) -> None:
        """Disconnect from Fyers."""
        self._log.info("Disconnecting from Fyers...")

        # Disconnect WebSocket
        if self._ws_client:
            await self._ws_client.disconnect()
            self._ws_client = None

        # Disconnect HTTP
        await self._http_client.disconnect()

        # Clear subscriptions
        self._subscribed_quotes.clear()
        self._subscribed_trades.clear()
        self._subscribed_bars.clear()
        self._symbol_map.clear()

        self._log.info("Disconnected from Fyers")

    # -------------------------------------------------------------------------
    # Subscriptions
    # -------------------------------------------------------------------------

    async def _subscribe_quote_ticks(self, instrument_id: InstrumentId) -> None:
        """Subscribe to quote ticks for an instrument."""
        fyers_symbol = to_fyers_symbol(instrument_id)

        # Track mapping
        self._symbol_map[fyers_symbol] = instrument_id

        # Subscribe via WebSocket
        await self._ws_client.subscribe([fyers_symbol], FyersDataType.DEPTH)
        self._subscribed_quotes.add(instrument_id)

        self._log.debug(f"Subscribed to quote ticks for {instrument_id}")

    async def _subscribe_trade_ticks(self, instrument_id: InstrumentId) -> None:
        """Subscribe to trade ticks for an instrument."""
        fyers_symbol = to_fyers_symbol(instrument_id)

        # Track mapping
        self._symbol_map[fyers_symbol] = instrument_id

        # Subscribe via WebSocket
        await self._ws_client.subscribe([fyers_symbol], FyersDataType.QUOTE)
        self._subscribed_trades.add(instrument_id)

        self._log.debug(f"Subscribed to trade ticks for {instrument_id}")

    async def _subscribe_bars(self, bar_type: BarType) -> None:
        """Subscribe to bars for an instrument."""
        instrument_id = bar_type.instrument_id
        fyers_symbol = to_fyers_symbol(instrument_id)

        # Track mapping
        self._symbol_map[fyers_symbol] = instrument_id
        self._subscribed_bars[bar_type] = instrument_id

        # Subscribe to quote data for bar aggregation
        await self._ws_client.subscribe([fyers_symbol], FyersDataType.QUOTE)

        self._log.debug(f"Subscribed to bars for {bar_type}")

    async def _unsubscribe_quote_ticks(self, instrument_id: InstrumentId) -> None:
        """Unsubscribe from quote ticks for an instrument."""
        fyers_symbol = to_fyers_symbol(instrument_id)

        await self._ws_client.unsubscribe([fyers_symbol])
        self._subscribed_quotes.discard(instrument_id)

        # Clean up mapping if no other subscriptions
        if instrument_id not in self._subscribed_trades:
            self._symbol_map.pop(fyers_symbol, None)

        self._log.debug(f"Unsubscribed from quote ticks for {instrument_id}")

    async def _unsubscribe_trade_ticks(self, instrument_id: InstrumentId) -> None:
        """Unsubscribe from trade ticks for an instrument."""
        fyers_symbol = to_fyers_symbol(instrument_id)

        await self._ws_client.unsubscribe([fyers_symbol])
        self._subscribed_trades.discard(instrument_id)

        # Clean up mapping if no other subscriptions
        if instrument_id not in self._subscribed_quotes:
            self._symbol_map.pop(fyers_symbol, None)

        self._log.debug(f"Unsubscribed from trade ticks for {instrument_id}")

    async def _unsubscribe_bars(self, bar_type: BarType) -> None:
        """Unsubscribe from bars."""
        instrument_id = bar_type.instrument_id
        fyers_symbol = to_fyers_symbol(instrument_id)

        self._subscribed_bars.pop(bar_type, None)

        # Only unsubscribe if no other bar types for this instrument
        other_bars = [bt for bt, iid in self._subscribed_bars.items() if iid == instrument_id]
        if not other_bars:
            await self._ws_client.unsubscribe([fyers_symbol])

        self._log.debug(f"Unsubscribed from bars for {bar_type}")

    # -------------------------------------------------------------------------
    # Data requests
    # -------------------------------------------------------------------------

    async def _request_bars(
        self,
        bar_type: BarType,
        limit: int,
        correlation_id: str,
        start: int | None = None,
        end: int | None = None,
    ) -> list[Bar]:
        """Request historical bars."""
        instrument_id = bar_type.instrument_id
        fyers_symbol = to_fyers_symbol(instrument_id)

        # Map bar spec to Fyers resolution
        resolution = self._map_resolution(bar_type)

        # Calculate time range
        end_ts = end or int(self._clock.timestamp())
        bar_secs = self._get_bar_seconds(bar_type)
        start_ts = start or (end_ts - limit * bar_secs)

        try:
            response = await self._http_client.get_history(
                symbol=fyers_symbol,
                resolution=resolution,
                from_ts=start_ts,
                to_ts=end_ts,
            )

            bars = []
            ts_init = self._clock.timestamp_ns()

            for candle in response.get("candles", []):
                bar = parse_bar(candle, instrument_id, bar_type, ts_init)
                bars.append(bar)

            self._log.debug(f"Received {len(bars)} bars for {bar_type}")
            return bars

        except Exception as e:
            self._log.error(f"Failed to request bars: {e}")
            return []

    async def _request_quote_ticks(
        self,
        instrument_id: InstrumentId,
        limit: int,
        correlation_id: str,
        start: int | None = None,
        end: int | None = None,
    ) -> list[QuoteTick]:
        """Request quote ticks (Fyers doesn't support historical ticks)."""
        self._log.warning("Fyers does not support historical quote tick data")
        return []

    async def _request_trade_ticks(
        self,
        instrument_id: InstrumentId,
        limit: int,
        correlation_id: str,
        start: int | None = None,
        end: int | None = None,
    ) -> list[TradeTick]:
        """Request trade ticks (Fyers doesn't support historical ticks)."""
        self._log.warning("Fyers does not support historical trade tick data")
        return []

    # -------------------------------------------------------------------------
    # WebSocket handlers
    # -------------------------------------------------------------------------

    def _handle_ws_message(self, data: dict[str, Any]) -> None:
        """Handle incoming WebSocket messages."""
        try:
            ts_init = self._clock.timestamp_ns()

            # Get symbol from message
            symbol = data.get("symbol", data.get("n", ""))
            if not symbol:
                # Check if it's a token-based message
                token = data.get("token")
                if token:
                    # Would need token-to-symbol mapping
                    return
                return

            # Look up instrument ID
            instrument_id = self._symbol_map.get(symbol)
            if not instrument_id:
                # Try to parse it
                instrument_id = parse_fyers_symbol(symbol)
                if not instrument_id:
                    return

            # Generate quote tick if subscribed
            if instrument_id in self._subscribed_quotes:
                quote = parse_quote_tick(data, instrument_id, ts_init)
                self._handle_data(quote)

            # Generate trade tick if subscribed
            if instrument_id in self._subscribed_trades:
                trade = parse_trade_tick(data, instrument_id, ts_init)
                self._handle_data(trade)

        except Exception as e:
            self._log.error(f"Error handling WebSocket message: {e}")

    def _handle_ws_error(self, error: Exception) -> None:
        """Handle WebSocket errors."""
        self._log.error(f"WebSocket error: {error}")

    # -------------------------------------------------------------------------
    # Utility methods
    # -------------------------------------------------------------------------

    def _map_resolution(self, bar_type: BarType) -> str:
        """Map BarType to Fyers resolution string."""
        spec = bar_type.spec
        step = spec.step

        # Get aggregation type name
        agg_name = str(spec.aggregation)

        if "MINUTE" in agg_name:
            # Fyers supports: 1, 2, 3, 5, 10, 15, 20, 30, 60, 120, 240
            if step in [1, 2, 3, 5, 10, 15, 20, 30]:
                return str(step)
            elif step == 60:
                return "60"
            elif step == 120:
                return "120"
            elif step == 240:
                return "240"
            else:
                return str(step)
        elif "HOUR" in agg_name:
            return str(step * 60)
        elif "DAY" in agg_name:
            return FyersResolution.DAY
        elif "WEEK" in agg_name:
            return FyersResolution.WEEK
        elif "MONTH" in agg_name:
            return FyersResolution.MONTH

        return "1"  # Default to 1 minute

    def _get_bar_seconds(self, bar_type: BarType) -> int:
        """Get number of seconds per bar."""
        spec = bar_type.spec
        step = spec.step
        agg_name = str(spec.aggregation)

        if "MINUTE" in agg_name:
            return step * 60
        elif "HOUR" in agg_name:
            return step * 3600
        elif "DAY" in agg_name:
            return step * 86400
        elif "WEEK" in agg_name:
            return step * 604800

        return 60  # Default
