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
Fyers client factories.
"""

import asyncio
from functools import lru_cache

from nautilus_trader.adapters.fyers.config import FyersDataClientConfig
from nautilus_trader.adapters.fyers.config import FyersExecClientConfig
from nautilus_trader.adapters.fyers.config import FyersInstrumentProviderConfig
from nautilus_trader.adapters.fyers.constants import FYERS_CLIENT_ID
from nautilus_trader.adapters.fyers.data import FyersDataClient
from nautilus_trader.adapters.fyers.execution import FyersExecutionClient
from nautilus_trader.adapters.fyers.http.client import FyersHttpClient
from nautilus_trader.adapters.fyers.providers import FyersInstrumentProvider
from nautilus_trader.cache.cache import Cache
from nautilus_trader.common.component import LiveClock
from nautilus_trader.common.component import Logger
from nautilus_trader.common.component import MessageBus
from nautilus_trader.live.factories import LiveDataClientFactory
from nautilus_trader.live.factories import LiveExecClientFactory


@lru_cache(1)
def get_cached_fyers_http_client(
    client_id: str,
    access_token: str,
    base_url: str | None = None,
) -> FyersHttpClient:
    """
    Get a cached Fyers HTTP client.

    This prevents duplicate HTTP client instances when creating
    multiple data/execution clients.

    Parameters
    ----------
    client_id : str
        The Fyers App ID.
    access_token : str
        The OAuth access token.
    base_url : str, optional
        The base URL override.

    Returns
    -------
    FyersHttpClient

    """
    return FyersHttpClient(
        client_id=client_id,
        access_token=access_token,
        base_url=base_url,
    )


@lru_cache(1)
def get_cached_fyers_instrument_provider(
    client_id: str,
    access_token: str,
    segments: tuple[str, ...] = ("NSE_CM", "NSE_FO"),
) -> FyersInstrumentProvider:
    """
    Get a cached Fyers instrument provider.

    Parameters
    ----------
    client_id : str
        The Fyers App ID.
    access_token : str
        The OAuth access token.
    segments : tuple[str, ...], default ("NSE_CM", "NSE_FO")
        The market segments to load.

    Returns
    -------
    FyersInstrumentProvider

    """
    config = FyersInstrumentProviderConfig(
        load_all=True,
        segments=list(segments),
    )
    return FyersInstrumentProvider(config=config)


class FyersLiveDataClientFactory(LiveDataClientFactory):
    """
    Factory for creating Fyers live data clients.

    Provides a ``create`` method for creating new Fyers data clients.
    """

    @staticmethod
    def create(
        loop: asyncio.AbstractEventLoop,
        name: str,
        config: FyersDataClientConfig,
        msgbus: MessageBus,
        cache: Cache,
        clock: LiveClock,
    ) -> FyersDataClient:
        """
        Create a new Fyers data client.

        Parameters
        ----------
        loop : asyncio.AbstractEventLoop
            The event loop.
        name : str
            The client name.
        config : FyersDataClientConfig
            The client configuration.
        msgbus : MessageBus
            The message bus.
        cache : Cache
            The cache.
        clock : LiveClock
            The clock.

        Returns
        -------
        FyersDataClient

        """
        # Get or create instrument provider
        instrument_provider = get_cached_fyers_instrument_provider(
            client_id=config.client_id,
            access_token=config.access_token,
            segments=tuple(config.instrument_provider.segments)
            if config.instrument_provider
            else ("NSE_CM", "NSE_FO"),
        )

        return FyersDataClient(
            loop=loop,
            client_id=FYERS_CLIENT_ID,
            msgbus=msgbus,
            cache=cache,
            clock=clock,
            instrument_provider=instrument_provider,
            config=config,
        )


class FyersLiveExecClientFactory(LiveExecClientFactory):
    """
    Factory for creating Fyers live execution clients.

    Provides a ``create`` method for creating new Fyers execution clients.
    """

    @staticmethod
    def create(
        loop: asyncio.AbstractEventLoop,
        name: str,
        config: FyersExecClientConfig,
        msgbus: MessageBus,
        cache: Cache,
        clock: LiveClock,
    ) -> FyersExecutionClient:
        """
        Create a new Fyers execution client.

        Parameters
        ----------
        loop : asyncio.AbstractEventLoop
            The event loop.
        name : str
            The client name.
        config : FyersExecClientConfig
            The client configuration.
        msgbus : MessageBus
            The message bus.
        cache : Cache
            The cache.
        clock : LiveClock
            The clock.

        Returns
        -------
        FyersExecutionClient

        """
        return FyersExecutionClient(
            loop=loop,
            client_id=FYERS_CLIENT_ID,
            msgbus=msgbus,
            cache=cache,
            clock=clock,
            config=config,
        )
