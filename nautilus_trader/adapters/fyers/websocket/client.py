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
Fyers WebSocket client for real-time market data.
"""

import asyncio
from collections.abc import Callable
from typing import Any

import msgspec

from nautilus_trader.adapters.fyers.constants import FYERS_DATA_WS_URL
from nautilus_trader.adapters.fyers.enums import FyersDataType
from nautilus_trader.common.component import Logger
from nautilus_trader.core.nautilus_pyo3 import WebSocketClient
from nautilus_trader.core.nautilus_pyo3 import WebSocketClientError
from nautilus_trader.core.nautilus_pyo3 import WebSocketConfig


class FyersWebSocketClient:
    """
    WebSocket client for Fyers real-time market data.

    Parameters
    ----------
    client_id : str
        The Fyers App ID.
    access_token : str
        The OAuth access token.
    on_message : Callable[[dict], None]
        The callback for received messages.
    on_error : Callable[[Exception], None], optional
        The callback for errors.
    ws_url : str, optional
        The WebSocket URL override.
    logger : Logger, optional
        The logger instance.
    heartbeat_interval : int, default 30
        The heartbeat interval in seconds.
    reconnect_delay : int, default 5
        The reconnection delay in seconds.
    max_reconnect_attempts : int, default 10
        The maximum reconnection attempts.

    """

    def __init__(
        self,
        client_id: str,
        access_token: str,
        on_message: Callable[[dict[str, Any]], None],
        on_error: Callable[[Exception], None] | None = None,
        ws_url: str | None = None,
        logger: Logger | None = None,
        heartbeat_interval: int = 30,
        reconnect_delay: int = 5,
        max_reconnect_attempts: int = 10,
    ) -> None:
        self._client_id = client_id
        self._access_token = access_token
        self._on_message = on_message
        self._on_error = on_error
        self._ws_url = ws_url or FYERS_DATA_WS_URL
        self._logger = logger
        self._heartbeat_interval = heartbeat_interval
        self._reconnect_delay = reconnect_delay
        self._max_reconnect_attempts = max_reconnect_attempts

        self._ws_client: WebSocketClient | None = None
        self._subscriptions: set[str] = set()
        self._subscription_modes: dict[str, FyersDataType] = {}
        self._running = False
        self._connected = False
        self._reconnect_task: asyncio.Task | None = None
        self._heartbeat_task: asyncio.Task | None = None

        self._decoder = msgspec.json.Decoder()
        self._encoder = msgspec.json.Encoder()

    @property
    def is_connected(self) -> bool:
        """Return whether the client is connected."""
        return self._connected

    @property
    def subscriptions(self) -> set[str]:
        """Return the current subscriptions."""
        return self._subscriptions.copy()

    async def connect(self) -> None:
        """Connect to the Fyers WebSocket server."""
        try:
            # Build WebSocket URL with authentication
            ws_url = self._build_ws_url()

            # Configure WebSocket
            config = WebSocketConfig(
                url=ws_url,
                handler=self._handle_message,
                heartbeat=self._heartbeat_interval,
            )

            # Create and connect
            self._ws_client = await WebSocketClient.connect(config)
            self._running = True
            self._connected = True

            if self._logger:
                self._logger.info("Connected to Fyers WebSocket")

            # Start heartbeat
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        except WebSocketClientError as e:
            self._connected = False
            if self._on_error:
                self._on_error(e)
            raise

    async def disconnect(self) -> None:
        """Disconnect from the Fyers WebSocket server."""
        self._running = False
        self._connected = False

        # Cancel tasks
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            self._heartbeat_task = None

        if self._reconnect_task:
            self._reconnect_task.cancel()
            self._reconnect_task = None

        # Close WebSocket
        if self._ws_client:
            await self._ws_client.disconnect()
            self._ws_client = None

        self._subscriptions.clear()
        self._subscription_modes.clear()

        if self._logger:
            self._logger.info("Disconnected from Fyers WebSocket")

    async def subscribe(
        self,
        symbols: list[str],
        data_type: FyersDataType = FyersDataType.QUOTE,
    ) -> None:
        """
        Subscribe to market data for symbols.

        Parameters
        ----------
        symbols : list[str]
            The Fyers symbols to subscribe to.
        data_type : FyersDataType, default QUOTE
            The type of data to subscribe to.

        """
        if not self._ws_client:
            raise RuntimeError("WebSocket not connected")

        # Build subscription message based on data type
        # Fyers uses different modes: 1=LTP, 2=Quote, 3=Depth
        mode = self._get_mode(data_type)

        subscribe_msg = {
            "T": "SUB_L2",  # or "SUB_L1" for LTP only
            "L2LIST": symbols if mode == 3 else [],
            "L1LIST": symbols if mode <= 2 else [],
            "SUB_T": mode,
        }

        await self._send(subscribe_msg)

        # Track subscriptions
        for symbol in symbols:
            self._subscriptions.add(symbol)
            self._subscription_modes[symbol] = data_type

        if self._logger:
            self._logger.debug(f"Subscribed to {len(symbols)} symbols")

    async def unsubscribe(self, symbols: list[str]) -> None:
        """
        Unsubscribe from market data for symbols.

        Parameters
        ----------
        symbols : list[str]
            The Fyers symbols to unsubscribe from.

        """
        if not self._ws_client:
            return

        unsubscribe_msg = {
            "T": "UNSUB_L2",
            "L2LIST": symbols,
            "L1LIST": symbols,
        }

        await self._send(unsubscribe_msg)

        # Remove from tracking
        for symbol in symbols:
            self._subscriptions.discard(symbol)
            self._subscription_modes.pop(symbol, None)

        if self._logger:
            self._logger.debug(f"Unsubscribed from {len(symbols)} symbols")

    def _build_ws_url(self) -> str:
        """Build the WebSocket URL with authentication parameters."""
        # Fyers WebSocket requires token in the connection URL
        return f"{self._ws_url}?access_token={self._client_id}:{self._access_token}"

    def _get_mode(self, data_type: FyersDataType) -> int:
        """Get the Fyers data mode from data type."""
        modes = {
            FyersDataType.LTP: 1,
            FyersDataType.QUOTE: 2,
            FyersDataType.DEPTH: 3,
        }
        return modes.get(data_type, 2)

    async def _send(self, message: dict[str, Any]) -> None:
        """Send a message through the WebSocket."""
        if self._ws_client:
            data = self._encoder.encode(message)
            await self._ws_client.send(data)

    def _handle_message(self, raw_data: bytes) -> None:
        """Handle incoming WebSocket messages."""
        try:
            # Fyers sends binary data that needs to be decoded
            # The format varies based on subscription type
            data = self._parse_message(raw_data)
            if data:
                self._on_message(data)

        except Exception as e:
            if self._logger:
                self._logger.error(f"Error handling message: {e}")
            if self._on_error:
                self._on_error(e)

    def _parse_message(self, raw_data: bytes) -> dict[str, Any] | None:
        """
        Parse the raw WebSocket message.

        Fyers sends data in a specific binary format for market data.
        This method handles both JSON and binary formats.
        """
        try:
            # Try JSON first (for control messages)
            return self._decoder.decode(raw_data)
        except msgspec.DecodeError:
            # Binary market data format
            return self._parse_binary_data(raw_data)

    def _parse_binary_data(self, data: bytes) -> dict[str, Any] | None:
        """
        Parse binary market data from Fyers.

        The binary format contains:
        - Symbol token (4 bytes)
        - LTP (4 bytes, float)
        - Open (4 bytes, float)
        - High (4 bytes, float)
        - Low (4 bytes, float)
        - Close (4 bytes, float)
        - Volume (4 bytes, int)
        - Timestamp (4 bytes, int)
        - Bid price (4 bytes, float)
        - Ask price (4 bytes, float)
        - Bid qty (4 bytes, int)
        - Ask qty (4 bytes, int)
        """
        import struct

        if len(data) < 48:  # Minimum expected size
            return None

        try:
            # Unpack the binary data
            # Format may vary - this is a common structure
            values = struct.unpack("<I f f f f f I I f f I I", data[:48])

            return {
                "token": values[0],
                "lp": values[1],         # Last price
                "open": values[2],
                "high": values[3],
                "low": values[4],
                "close": values[5],
                "volume": values[6],
                "timestamp": values[7],
                "bp": values[8],         # Bid price
                "ap": values[9],         # Ask price
                "bq": values[10],        # Bid quantity
                "aq": values[11],        # Ask quantity
            }
        except struct.error:
            return None

    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeat messages."""
        while self._running:
            try:
                await asyncio.sleep(self._heartbeat_interval)
                if self._ws_client and self._connected:
                    await self._send({"T": "HB"})

            except asyncio.CancelledError:
                break
            except Exception as e:
                if self._logger:
                    self._logger.error(f"Heartbeat error: {e}")

    async def _reconnect(self) -> None:
        """Attempt to reconnect to the WebSocket server."""
        for attempt in range(self._max_reconnect_attempts):
            try:
                delay = self._reconnect_delay * (attempt + 1)
                if self._logger:
                    self._logger.info(f"Reconnecting in {delay}s (attempt {attempt + 1})")

                await asyncio.sleep(delay)
                await self.connect()

                # Resubscribe
                if self._subscriptions:
                    for symbol, mode in self._subscription_modes.items():
                        await self.subscribe([symbol], mode)

                if self._logger:
                    self._logger.info("Reconnected successfully")
                return

            except Exception as e:
                if self._logger:
                    self._logger.error(f"Reconnection attempt {attempt + 1} failed: {e}")

        raise RuntimeError(f"Failed to reconnect after {self._max_reconnect_attempts} attempts")
