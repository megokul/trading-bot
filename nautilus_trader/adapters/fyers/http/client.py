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
Fyers HTTP client for REST API.
"""

import hashlib
from typing import Any

import msgspec

from nautilus_trader.adapters.fyers.constants import FYERS_HTTP_URL
from nautilus_trader.adapters.fyers.http.error import FyersApiError
from nautilus_trader.adapters.fyers.http.error import FyersAuthenticationError
from nautilus_trader.adapters.fyers.http.error import FyersConnectionError
from nautilus_trader.adapters.fyers.http.error import FyersRateLimitError
from nautilus_trader.common.component import Logger
from nautilus_trader.core.nautilus_pyo3 import HttpClient
from nautilus_trader.core.nautilus_pyo3 import HttpMethod
from nautilus_trader.core.nautilus_pyo3 import HttpResponse


class FyersHttpClient:
    """
    HTTP client for Fyers REST API.

    Parameters
    ----------
    client_id : str
        The Fyers App ID.
    access_token : str
        The OAuth access token.
    base_url : str, optional
        The base URL override.
    logger : Logger, optional
        The logger instance.

    """

    def __init__(
        self,
        client_id: str,
        access_token: str,
        base_url: str | None = None,
        logger: Logger | None = None,
    ) -> None:
        self._client_id = client_id
        self._access_token = access_token
        self._base_url = base_url or FYERS_HTTP_URL
        self._logger = logger
        self._http_client: HttpClient | None = None
        self._decoder = msgspec.json.Decoder()
        self._encoder = msgspec.json.Encoder()

    @property
    def _headers(self) -> dict[str, str]:
        """Return the request headers."""
        return {
            "Authorization": f"{self._client_id}:{self._access_token}",
            "Content-Type": "application/json",
        }

    async def connect(self) -> None:
        """Connect the HTTP client."""
        self._http_client = HttpClient()

    async def disconnect(self) -> None:
        """Disconnect the HTTP client."""
        self._http_client = None

    def _check_connected(self) -> None:
        """Check if the client is connected."""
        if self._http_client is None:
            raise FyersConnectionError("HTTP client not connected")

    async def _request(
        self,
        method: HttpMethod,
        endpoint: str,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Send an HTTP request to the Fyers API.

        Parameters
        ----------
        method : HttpMethod
            The HTTP method.
        endpoint : str
            The API endpoint.
        params : dict, optional
            The query parameters.
        data : dict, optional
            The request body data.

        Returns
        -------
        dict
            The response data.

        Raises
        ------
        FyersApiError
            If the API returns an error.

        """
        self._check_connected()

        url = f"{self._base_url}{endpoint}"

        # Build query string
        if params:
            query_parts = [f"{k}={v}" for k, v in params.items()]
            url = f"{url}?{'&'.join(query_parts)}"

        # Encode body
        body = self._encoder.encode(data) if data else None

        # Send request
        response: HttpResponse = await self._http_client.request(
            method=method,
            url=url,
            headers=self._headers,
            body=body,
        )

        # Parse response
        result = self._decoder.decode(response.body)

        # Check for errors
        status = result.get("s", "")
        if status != "ok":
            code = result.get("code", -1)
            message = result.get("message", "Unknown error")

            # Check for specific error types
            if code in (-16, -17, -18):  # Auth errors
                raise FyersAuthenticationError(message)
            elif code == -50:  # Rate limit
                raise FyersRateLimitError(message)
            else:
                raise FyersApiError(code=code, message=message)

        return result

    # -------------------------------------------------------------------------
    # Account endpoints
    # -------------------------------------------------------------------------

    async def get_profile(self) -> dict[str, Any]:
        """
        Get user profile information.

        Returns
        -------
        dict
            The profile data.

        """
        return await self._request(HttpMethod.GET, "/profile")

    async def get_funds(self) -> dict[str, Any]:
        """
        Get available funds and margins.

        Returns
        -------
        dict
            The funds data.

        """
        return await self._request(HttpMethod.GET, "/funds")

    # -------------------------------------------------------------------------
    # Order endpoints
    # -------------------------------------------------------------------------

    async def place_order(self, order: dict[str, Any]) -> dict[str, Any]:
        """
        Place a single order.

        Parameters
        ----------
        order : dict
            The order details.

        Returns
        -------
        dict
            The order response with order ID.

        """
        return await self._request(HttpMethod.POST, "/orders", data=order)

    async def place_multi_order(self, orders: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Place multiple orders (up to 10).

        Parameters
        ----------
        orders : list[dict]
            The list of order details.

        Returns
        -------
        dict
            The response with order IDs.

        """
        return await self._request(HttpMethod.POST, "/orders/multi", data={"orders": orders})

    async def modify_order(self, order_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        """
        Modify an existing order.

        Parameters
        ----------
        order_id : str
            The order ID to modify.
        updates : dict
            The fields to update.

        Returns
        -------
        dict
            The modification response.

        """
        updates["id"] = order_id
        return await self._request(HttpMethod.PUT, "/orders", data=updates)

    async def cancel_order(self, order_id: str) -> dict[str, Any]:
        """
        Cancel an order.

        Parameters
        ----------
        order_id : str
            The order ID to cancel.

        Returns
        -------
        dict
            The cancellation response.

        """
        return await self._request(HttpMethod.DELETE, "/orders", data={"id": order_id})

    async def get_orders(self) -> dict[str, Any]:
        """
        Get all orders for the day.

        Returns
        -------
        dict
            The orders list.

        """
        return await self._request(HttpMethod.GET, "/orders")

    async def get_order(self, order_id: str) -> dict[str, Any]:
        """
        Get a specific order by ID.

        Parameters
        ----------
        order_id : str
            The order ID.

        Returns
        -------
        dict
            The order details.

        """
        return await self._request(HttpMethod.GET, "/orders", params={"id": order_id})

    # -------------------------------------------------------------------------
    # Position endpoints
    # -------------------------------------------------------------------------

    async def get_positions(self) -> dict[str, Any]:
        """
        Get all positions.

        Returns
        -------
        dict
            The positions list.

        """
        return await self._request(HttpMethod.GET, "/positions")

    async def convert_position(
        self,
        symbol: str,
        position_side: int,
        convert_qty: int,
        convert_from: str,
        convert_to: str,
    ) -> dict[str, Any]:
        """
        Convert position product type (e.g., INTRADAY to CNC).

        Parameters
        ----------
        symbol : str
            The Fyers symbol.
        position_side : int
            The position side (1=long, -1=short).
        convert_qty : int
            The quantity to convert.
        convert_from : str
            The source product type.
        convert_to : str
            The target product type.

        Returns
        -------
        dict
            The conversion response.

        """
        data = {
            "symbol": symbol,
            "positionSide": position_side,
            "convertQty": convert_qty,
            "convertFrom": convert_from,
            "convertTo": convert_to,
        }
        return await self._request(HttpMethod.POST, "/positions/convert", data=data)

    async def exit_position(self, symbol: str) -> dict[str, Any]:
        """
        Exit a position for a symbol.

        Parameters
        ----------
        symbol : str
            The Fyers symbol.

        Returns
        -------
        dict
            The exit response.

        """
        return await self._request(HttpMethod.POST, "/positions/exit", data={"symbol": symbol})

    async def exit_all_positions(self) -> dict[str, Any]:
        """
        Exit all open positions.

        Returns
        -------
        dict
            The exit response.

        """
        return await self._request(HttpMethod.POST, "/positions/exit-all")

    # -------------------------------------------------------------------------
    # Holdings endpoints
    # -------------------------------------------------------------------------

    async def get_holdings(self) -> dict[str, Any]:
        """
        Get equity holdings.

        Returns
        -------
        dict
            The holdings list.

        """
        return await self._request(HttpMethod.GET, "/holdings")

    # -------------------------------------------------------------------------
    # Trade endpoints
    # -------------------------------------------------------------------------

    async def get_tradebook(self) -> dict[str, Any]:
        """
        Get trade book (executed trades).

        Returns
        -------
        dict
            The trades list.

        """
        return await self._request(HttpMethod.GET, "/tradebook")

    # -------------------------------------------------------------------------
    # Market data endpoints
    # -------------------------------------------------------------------------

    async def get_quotes(self, symbols: list[str]) -> dict[str, Any]:
        """
        Get current quotes for symbols.

        Parameters
        ----------
        symbols : list[str]
            List of Fyers symbols.

        Returns
        -------
        dict
            The quotes data.

        """
        return await self._request(
            HttpMethod.GET,
            "/quotes",
            params={"symbols": ",".join(symbols)},
        )

    async def get_depth(self, symbol: str) -> dict[str, Any]:
        """
        Get market depth (L2 order book) for a symbol.

        Parameters
        ----------
        symbol : str
            The Fyers symbol.

        Returns
        -------
        dict
            The market depth data.

        """
        return await self._request(
            HttpMethod.GET,
            "/depth",
            params={"symbol": symbol, "ohlcv_flag": 1},
        )

    async def get_history(
        self,
        symbol: str,
        resolution: str,
        from_ts: int,
        to_ts: int,
        cont_flag: int = 1,
    ) -> dict[str, Any]:
        """
        Get historical candle data.

        Parameters
        ----------
        symbol : str
            The Fyers symbol.
        resolution : str
            The candle resolution (1, 5, 15, 30, 60, D, W, M).
        from_ts : int
            The start timestamp (Unix epoch seconds).
        to_ts : int
            The end timestamp (Unix epoch seconds).
        cont_flag : int, default 1
            Continuous data flag.

        Returns
        -------
        dict
            The candle data.

        """
        return await self._request(
            HttpMethod.GET,
            "/history",
            params={
                "symbol": symbol,
                "resolution": resolution,
                "date_format": 1,
                "range_from": from_ts,
                "range_to": to_ts,
                "cont_flag": cont_flag,
            },
        )

    async def get_market_status(self) -> dict[str, Any]:
        """
        Get current market status.

        Returns
        -------
        dict
            The market status.

        """
        return await self._request(HttpMethod.GET, "/market-status")

    # -------------------------------------------------------------------------
    # Utility methods
    # -------------------------------------------------------------------------

    @staticmethod
    def generate_app_id_hash(client_id: str, secret_key: str) -> str:
        """
        Generate the app ID hash for authentication.

        Parameters
        ----------
        client_id : str
            The Fyers App ID.
        secret_key : str
            The Fyers App Secret.

        Returns
        -------
        str
            The SHA-256 hash.

        """
        combined = f"{client_id}:{secret_key}"
        return hashlib.sha256(combined.encode()).hexdigest()
