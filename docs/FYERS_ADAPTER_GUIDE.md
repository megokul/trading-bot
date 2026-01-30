# Fyers Adapter Implementation Guide for NautilusTrader

This document provides a comprehensive guide for implementing a Fyers adapter to enable trading on NSE (National Stock Exchange of India) through NautilusTrader.

## Table of Contents

1. [Fyers API Overview](#fyers-api-overview)
2. [Authentication Flow](#authentication-flow)
3. [API Endpoints](#api-endpoints)
4. [Symbol Format](#symbol-format)
5. [Adapter Architecture](#adapter-architecture)
6. [Implementation Guide](#implementation-guide)
7. [Testing Strategy](#testing-strategy)

---

## Fyers API Overview

### Supported Markets
- **NSE**: Equity, F&O (Futures & Options), Currency
- **BSE**: Equity only
- **MCX**: Commodities

### API Capabilities
- **REST API**: Orders, positions, holdings, historical data, market quotes
- **WebSocket API**: Real-time market data (TBT - Tick-By-Tick)
- **Order Types**: Market, Limit, Stop-Loss, Stop-Loss Market, Bracket, Cover
- **Rate Limits**: Up to 100,000 requests per day, order placement < 75ms

### Key URLs
- **API Portal**: https://myapi.fyers.in/
- **Documentation**: https://myapi.fyers.in/docsv3
- **WebSocket**: `wss://rtsocket-api.fyers.in/versova`
- **REST Base URL**: `https://api-t1.fyers.in/api/v3`

---

## Authentication Flow

### OAuth 2.0 Flow

Fyers uses OAuth 2.0 with daily token refresh requirement (SEBI compliance - tokens expire at 3:00 AM IST).

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Client    │────>│   Fyers     │────>│   User      │
│   App       │     │   Auth      │     │   Login     │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │
       │  1. Generate      │                   │
       │     Auth URL      │                   │
       │                   │                   │
       │                   │  2. User Login    │
       │                   │     with 2FA/TOTP │
       │                   │                   │
       │  3. Redirect with │                   │
       │     auth_code     │<──────────────────│
       │                   │                   │
       │  4. Exchange      │                   │
       │     auth_code     │                   │
       │     for token     │                   │
       │                   │                   │
       │  5. Access Token  │                   │
       │<──────────────────│                   │
       │                   │                   │
└──────┴───────────────────┴───────────────────┘
```

### Required Credentials

```python
# From Fyers Developer Dashboard (https://myapi.fyers.in/dashboard/)
client_id = "XXXXXX-100"           # App ID
secret_key = "XXXXXXXXXXXXXXXX"     # App Secret
redirect_uri = "https://your-redirect-uri.com"

# User Credentials
fyers_id = "FY12345"                # Fyers Client ID
pin = "1234"                        # 4-digit PIN
totp_key = "BASE32SECRETKEY"        # External 2FA TOTP Key
```

### Token Generation

```python
# Step 1: Generate Authorization URL
from fyers_apiv3 import fyersModel

session = fyersModel.SessionModel(
    client_id=client_id,
    secret_key=secret_key,
    redirect_uri=redirect_uri,
    response_type="code",
    grant_type="authorization_code"
)
auth_url = session.generate_authcode()

# Step 2: User authenticates and receives auth_code via redirect

# Step 3: Exchange auth_code for access_token
session.set_token(auth_code)
response = session.generate_token()
access_token = response["access_token"]

# Step 4: Create API instance
fyers = fyersModel.FyersModel(
    client_id=client_id,
    token=access_token,
    is_async=False
)
```

### App ID Hash Generation

For certain endpoints, you need `appIdHash`:

```python
import hashlib

def generate_app_id_hash(client_id: str, secret_key: str) -> str:
    """SHA-256 hash of client_id + secret_key"""
    combined = f"{client_id}:{secret_key}"
    return hashlib.sha256(combined.encode()).hexdigest()
```

---

## API Endpoints

### REST API Base URL
```
https://api-t1.fyers.in/api/v3
```

### Authentication Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/generate-authcode` | GET | Generate authorization URL |
| `/validate-authcode` | POST | Exchange auth_code for token |
| `/validate-refresh-token` | POST | Refresh access token |

### Account Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/profile` | GET | Get user profile |
| `/funds` | GET | Get available funds/margins |

### Order Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/orders` | POST | Place single order |
| `/orders/multi` | POST | Place multiple orders (up to 10) |
| `/orders/{order_id}` | PUT | Modify order |
| `/orders/{order_id}` | DELETE | Cancel order |
| `/orders` | GET | Get all orders |
| `/orders/{order_id}` | GET | Get specific order |

### Position Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/positions` | GET | Get all positions |
| `/positions/convert` | POST | Convert position (MIS↔CNC) |
| `/positions/exit` | POST | Exit position |
| `/positions/exit-all` | POST | Exit all positions |

### Holdings Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/holdings` | GET | Get equity holdings |

### Trade Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/tradebook` | GET | Get trade book |

### Market Data Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/quotes` | GET | Get current quotes |
| `/depth` | GET | Get market depth (L2) |
| `/history` | GET | Get historical candles |
| `/market-status` | GET | Get exchange status |

### Request Headers

```http
Authorization: {client_id}:{access_token}
Content-Type: application/json
```

---

## Symbol Format

### General Format
```
EXCHANGE:SYMBOL-SERIES
```

### Equity (Cash Segment)

| Exchange | Format | Example |
|----------|--------|---------|
| NSE | `NSE:SYMBOL-EQ` | `NSE:RELIANCE-EQ`, `NSE:SBIN-EQ` |
| BSE | `BSE:SYMBOL-A` | `BSE:RELIANCE-A` |

### Index

| Index | Symbol |
|-------|--------|
| Nifty 50 | `NSE:NIFTY50-INDEX` |
| Bank Nifty | `NSE:NIFTYBANK-INDEX` |
| Sensex | `BSE:SENSEX-INDEX` |

### Futures

Format: `EXCHANGE:SYMBOL{YY}{MMM}FUT`

| Type | Example |
|------|---------|
| Stock Future | `NSE:SBIN25JANFUT` |
| Index Future | `NSE:NIFTY25JANFUT` |
| Currency Future | `NSE:USDINR25JANFUT` |
| Commodity Future | `MCX:GOLD25FEBFUT` |

### Options

Format: `EXCHANGE:SYMBOL{YY}{MMM}{STRIKE}{CE/PE}`

| Type | Example |
|------|---------|
| Nifty Call | `NSE:NIFTY25JAN23000CE` |
| Nifty Put | `NSE:NIFTY25JAN22500PE` |
| Bank Nifty Call | `NSE:BANKNIFTY25JAN48000CE` |
| Stock Option | `NSE:RELIANCE25JAN2800CE` |

### Symbol Token Lookup

Fyers uses numeric tokens internally. Use the symbol master file:
```
https://public.fyers.in/sym_details/NSE_CM.csv  # NSE Cash
https://public.fyers.in/sym_details/NSE_FO.csv  # NSE F&O
https://public.fyers.in/sym_details/BSE_CM.csv  # BSE Cash
https://public.fyers.in/sym_details/MCX_COM.csv # MCX Commodity
```

---

## Adapter Architecture

### Directory Structure

```
nautilus_trader/adapters/fyers/
├── __init__.py
├── config.py                 # Configuration classes
├── constants.py              # Venue constants, URLs
├── enums.py                  # Fyers-specific enums
├── error.py                  # Error types
├── factories.py              # Client factories
├── parsing.py                # Type conversion functions
├── symbol.py                 # Symbol parsing utilities
├── http/
│   ├── __init__.py
│   ├── client.py             # HTTP client wrapper
│   ├── endpoints.py          # Endpoint definitions
│   └── errors.py             # HTTP-specific errors
├── websocket/
│   ├── __init__.py
│   ├── client.py             # WebSocket client
│   ├── handler.py            # Message handler
│   └── messages.py           # Message types
├── data.py                   # FyersDataClient
├── execution.py              # FyersExecutionClient
└── providers.py              # FyersInstrumentProvider
```

### Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                     NautilusTrader Core                      │
├─────────────────────────────────────────────────────────────┤
│  DataEngine  │  ExecutionEngine  │  Cache  │  MessageBus    │
└──────┬───────┴────────┬──────────┴────┬────┴───────┬────────┘
       │                │               │            │
       ▼                ▼               │            │
┌──────────────┐ ┌──────────────┐      │            │
│FyersDataClient│ │FyersExecClient│     │            │
├──────────────┤ ├──────────────┤      │            │
│- subscribe   │ │- submit_order│      │            │
│- request_bars│ │- cancel_order│      │            │
│- quotes      │ │- modify_order│      │            │
└──────┬───────┘ └──────┬───────┘      │            │
       │                │               │            │
       ▼                ▼               │            │
┌─────────────────────────────────────────────────────┐
│              FyersHttpClient                         │
├─────────────────────────────────────────────────────┤
│  - Authentication (OAuth 2.0)                        │
│  - Rate limiting (100K/day)                          │
│  - Request signing                                   │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│              FyersWebSocketClient                    │
├─────────────────────────────────────────────────────┤
│  - Real-time market data (TBT)                       │
│  - Order updates                                     │
│  - Connection management                             │
└─────────────────────────────────────────────────────┘
```

---

## Implementation Guide

### 1. Constants (`constants.py`)

```python
from nautilus_trader.model.identifiers import Venue

# Venue identifier
FYERS = "FYERS"
FYERS_VENUE = Venue(FYERS)

# API URLs
HTTP_URL = "https://api-t1.fyers.in/api/v3"
WS_URL = "wss://rtsocket-api.fyers.in/versova"

# Symbol master URLs
SYMBOL_MASTER_NSE_CM = "https://public.fyers.in/sym_details/NSE_CM.csv"
SYMBOL_MASTER_NSE_FO = "https://public.fyers.in/sym_details/NSE_FO.csv"
SYMBOL_MASTER_BSE_CM = "https://public.fyers.in/sym_details/BSE_CM.csv"
SYMBOL_MASTER_MCX = "https://public.fyers.in/sym_details/MCX_COM.csv"

# Rate limits
MAX_REQUESTS_PER_DAY = 100_000
MAX_ORDERS_PER_SECOND = 10

# Trading hours (IST)
MARKET_OPEN = "09:15"
MARKET_CLOSE = "15:30"
```

### 2. Enums (`enums.py`)

```python
from enum import Enum

class FyersExchange(str, Enum):
    NSE = "NSE"
    BSE = "BSE"
    MCX = "MCX"

class FyersSegment(str, Enum):
    CM = "CM"       # Cash/Capital Market
    FO = "FO"       # Futures & Options
    CD = "CD"       # Currency Derivatives
    COM = "COM"     # Commodities

class FyersProductType(str, Enum):
    CNC = "CNC"     # Cash and Carry (delivery)
    INTRADAY = "INTRADAY"  # Intraday/MIS
    MARGIN = "MARGIN"      # Margin trading
    CO = "CO"       # Cover Order
    BO = "BO"       # Bracket Order

class FyersOrderType(int, Enum):
    LIMIT = 1
    MARKET = 2
    STOP_LOSS_MARKET = 3  # SL-M
    STOP_LOSS_LIMIT = 4   # SL-L

class FyersOrderSide(int, Enum):
    BUY = 1
    SELL = -1

class FyersOrderStatus(int, Enum):
    CANCELLED = 1
    TRADED = 2        # Filled
    TRANSIT = 3       # In transit to exchange
    REJECTED = 4
    PENDING = 5
    EXPIRED = 6
    PARTIALLY_FILLED = 7

class FyersValidity(str, Enum):
    DAY = "DAY"
    IOC = "IOC"       # Immediate or Cancel
```

### 3. Configuration (`config.py`)

```python
from nautilus_trader.config import NautilusConfig
from nautilus_trader.live.config import LiveDataClientConfig, LiveExecClientConfig

class FyersDataClientConfig(LiveDataClientConfig, frozen=True):
    """Configuration for Fyers data client."""

    client_id: str                          # App ID from Fyers
    access_token: str                       # OAuth access token

    # Optional overrides
    base_url_http: str | None = None
    base_url_ws: str | None = None

    # Instrument loading
    load_instruments_on_start: bool = True
    instrument_segments: list[str] = ["NSE_CM", "NSE_FO"]

    # WebSocket settings
    ws_heartbeat_interval_secs: int = 30
    ws_reconnect_delay_secs: int = 5
    ws_max_reconnect_attempts: int = 10

    # Rate limiting
    max_requests_per_day: int = 100_000


class FyersExecClientConfig(LiveExecClientConfig, frozen=True):
    """Configuration for Fyers execution client."""

    client_id: str                          # App ID from Fyers
    access_token: str                       # OAuth access token

    # Account settings
    default_product_type: str = "INTRADAY"  # CNC, INTRADAY, MARGIN

    # Optional overrides
    base_url_http: str | None = None

    # Order settings
    max_order_rate: int = 10                # Orders per second


class FyersInstrumentProviderConfig(NautilusConfig, frozen=True):
    """Configuration for instrument provider."""

    load_all: bool = False
    load_ids: frozenset[str] | None = None
    segments: list[str] = ["NSE_CM", "NSE_FO"]
    filters: dict | None = None
```

### 4. Symbol Parsing (`symbol.py`)

```python
import re
from nautilus_trader.model.identifiers import InstrumentId, Symbol
from .constants import FYERS_VENUE

def parse_fyers_symbol(fyers_symbol: str) -> InstrumentId:
    """
    Parse Fyers symbol to NautilusTrader InstrumentId.

    Examples:
        NSE:RELIANCE-EQ -> RELIANCE-EQ.FYERS
        NSE:NIFTY25JAN23000CE -> NIFTY25JAN23000CE.FYERS
    """
    if ":" in fyers_symbol:
        exchange, symbol = fyers_symbol.split(":", 1)
    else:
        symbol = fyers_symbol

    return InstrumentId(Symbol(symbol), FYERS_VENUE)


def to_fyers_symbol(instrument_id: InstrumentId, exchange: str = "NSE") -> str:
    """
    Convert NautilusTrader InstrumentId to Fyers symbol format.

    Examples:
        RELIANCE-EQ.FYERS -> NSE:RELIANCE-EQ
    """
    symbol = instrument_id.symbol.value
    return f"{exchange}:{symbol}"


def parse_option_symbol(symbol: str) -> dict:
    """
    Parse option symbol to extract components.

    Example: NIFTY25JAN23000CE
    Returns: {
        'underlying': 'NIFTY',
        'expiry_year': '25',
        'expiry_month': 'JAN',
        'strike': 23000,
        'option_type': 'CE'
    }
    """
    pattern = r"^([A-Z]+)(\d{2})([A-Z]{3})(\d+)(CE|PE)$"
    match = re.match(pattern, symbol)

    if match:
        return {
            'underlying': match.group(1),
            'expiry_year': match.group(2),
            'expiry_month': match.group(3),
            'strike': int(match.group(4)),
            'option_type': match.group(5)
        }
    return None


def parse_futures_symbol(symbol: str) -> dict:
    """
    Parse futures symbol to extract components.

    Example: NIFTY25JANFUT
    Returns: {
        'underlying': 'NIFTY',
        'expiry_year': '25',
        'expiry_month': 'JAN'
    }
    """
    pattern = r"^([A-Z]+)(\d{2})([A-Z]{3})FUT$"
    match = re.match(pattern, symbol)

    if match:
        return {
            'underlying': match.group(1),
            'expiry_year': match.group(2),
            'expiry_month': match.group(3)
        }
    return None
```

### 5. HTTP Client (`http/client.py`)

```python
import hashlib
import aiohttp
from typing import Any
from nautilus_trader.common.component import Logger

class FyersHttpClient:
    """HTTP client for Fyers REST API."""

    def __init__(
        self,
        client_id: str,
        access_token: str,
        base_url: str | None = None,
        logger: Logger | None = None,
    ):
        self._client_id = client_id
        self._access_token = access_token
        self._base_url = base_url or "https://api-t1.fyers.in/api/v3"
        self._logger = logger
        self._session: aiohttp.ClientSession | None = None

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"{self._client_id}:{self._access_token}",
            "Content-Type": "application/json",
        }

    async def connect(self) -> None:
        self._session = aiohttp.ClientSession(headers=self._headers)

    async def disconnect(self) -> None:
        if self._session:
            await self._session.close()
            self._session = None

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict | None = None,
        data: dict | None = None,
    ) -> dict[str, Any]:
        url = f"{self._base_url}{endpoint}"

        async with self._session.request(
            method=method,
            url=url,
            params=params,
            json=data,
        ) as response:
            result = await response.json()

            if result.get("s") != "ok":
                raise FyersApiError(
                    code=result.get("code", -1),
                    message=result.get("message", "Unknown error"),
                )

            return result

    # Account endpoints
    async def get_profile(self) -> dict:
        return await self._request("GET", "/profile")

    async def get_funds(self) -> dict:
        return await self._request("GET", "/funds")

    # Order endpoints
    async def place_order(self, order: dict) -> dict:
        return await self._request("POST", "/orders", data=order)

    async def modify_order(self, order_id: str, updates: dict) -> dict:
        return await self._request("PUT", f"/orders/{order_id}", data=updates)

    async def cancel_order(self, order_id: str) -> dict:
        return await self._request("DELETE", f"/orders/{order_id}")

    async def get_orders(self) -> dict:
        return await self._request("GET", "/orders")

    async def get_order(self, order_id: str) -> dict:
        return await self._request("GET", f"/orders/{order_id}")

    # Position endpoints
    async def get_positions(self) -> dict:
        return await self._request("GET", "/positions")

    async def convert_position(self, data: dict) -> dict:
        return await self._request("POST", "/positions/convert", data=data)

    async def exit_position(self, data: dict) -> dict:
        return await self._request("POST", "/positions/exit", data=data)

    # Holdings endpoints
    async def get_holdings(self) -> dict:
        return await self._request("GET", "/holdings")

    # Market data endpoints
    async def get_quotes(self, symbols: list[str]) -> dict:
        return await self._request(
            "GET",
            "/quotes",
            params={"symbols": ",".join(symbols)}
        )

    async def get_depth(self, symbol: str) -> dict:
        return await self._request(
            "GET",
            "/depth",
            params={"symbol": symbol, "ohlcv_flag": 1}
        )

    async def get_history(
        self,
        symbol: str,
        resolution: str,
        from_ts: int,
        to_ts: int,
    ) -> dict:
        return await self._request(
            "GET",
            "/history",
            params={
                "symbol": symbol,
                "resolution": resolution,
                "date_format": 1,
                "range_from": from_ts,
                "range_to": to_ts,
                "cont_flag": 1,
            }
        )

    async def get_market_status(self) -> dict:
        return await self._request("GET", "/market-status")


class FyersApiError(Exception):
    """Fyers API error."""

    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(f"Fyers API Error [{code}]: {message}")
```

### 6. WebSocket Client (`websocket/client.py`)

```python
import asyncio
import json
from typing import Callable
import websockets
from nautilus_trader.common.component import Logger

class FyersWebSocketClient:
    """WebSocket client for Fyers real-time data."""

    def __init__(
        self,
        client_id: str,
        access_token: str,
        on_message: Callable[[dict], None],
        on_error: Callable[[Exception], None] | None = None,
        ws_url: str | None = None,
        logger: Logger | None = None,
    ):
        self._client_id = client_id
        self._access_token = access_token
        self._on_message = on_message
        self._on_error = on_error
        self._ws_url = ws_url or "wss://rtsocket-api.fyers.in/versova"
        self._logger = logger

        self._ws = None
        self._subscriptions: set[str] = set()
        self._running = False
        self._reconnect_task = None

    async def connect(self) -> None:
        """Connect to WebSocket and authenticate."""
        try:
            self._ws = await websockets.connect(self._ws_url)
            self._running = True

            # Send authentication
            auth_msg = {
                "T": "c",
                "uid": self._client_id,
                "actid": self._client_id,
                "token": self._access_token,
            }
            await self._ws.send(json.dumps(auth_msg))

            # Start message loop
            asyncio.create_task(self._message_loop())

        except Exception as e:
            if self._on_error:
                self._on_error(e)
            raise

    async def disconnect(self) -> None:
        """Disconnect from WebSocket."""
        self._running = False
        if self._ws:
            await self._ws.close()
            self._ws = None

    async def subscribe(self, symbols: list[str], data_type: str = "quote") -> None:
        """
        Subscribe to market data.

        data_type options:
        - "quote": LTP, volume, OI
        - "depth": Full market depth
        """
        if not self._ws:
            raise RuntimeError("WebSocket not connected")

        # Fyers data mode: 1=LTP, 2=Quote, 3=Depth
        mode = 3 if data_type == "depth" else 2

        subscribe_msg = {
            "T": "sub",
            "L1": symbols if mode <= 2 else [],
            "L2": symbols if mode == 3 else [],
        }
        await self._ws.send(json.dumps(subscribe_msg))
        self._subscriptions.update(symbols)

    async def unsubscribe(self, symbols: list[str]) -> None:
        """Unsubscribe from market data."""
        if not self._ws:
            return

        unsub_msg = {
            "T": "unsub",
            "L1": symbols,
            "L2": symbols,
        }
        await self._ws.send(json.dumps(unsub_msg))
        self._subscriptions -= set(symbols)

    async def _message_loop(self) -> None:
        """Process incoming WebSocket messages."""
        while self._running and self._ws:
            try:
                message = await self._ws.recv()
                data = json.loads(message)
                self._on_message(data)

            except websockets.ConnectionClosed:
                if self._running:
                    await self._reconnect()
                break
            except Exception as e:
                if self._on_error:
                    self._on_error(e)

    async def _reconnect(self) -> None:
        """Attempt to reconnect to WebSocket."""
        for attempt in range(10):
            try:
                await asyncio.sleep(5 * (attempt + 1))
                await self.connect()

                # Resubscribe
                if self._subscriptions:
                    await self.subscribe(list(self._subscriptions))

                return
            except Exception:
                continue

        raise RuntimeError("Failed to reconnect after 10 attempts")
```

### 7. Type Conversion (`parsing.py`)

```python
from decimal import Decimal
from nautilus_trader.core.datetime import millis_to_nanos
from nautilus_trader.model.data import Bar, BarType, QuoteTick, TradeTick
from nautilus_trader.model.enums import (
    OrderSide, OrderStatus, OrderType, TimeInForce,
    AggressorSide, PriceType,
)
from nautilus_trader.model.identifiers import InstrumentId, TradeId
from nautilus_trader.model.objects import Price, Quantity

from .enums import FyersOrderSide, FyersOrderStatus, FyersOrderType, FyersValidity


def parse_order_side(fyers_side: int) -> OrderSide:
    """Convert Fyers order side to Nautilus."""
    return OrderSide.BUY if fyers_side == 1 else OrderSide.SELL


def to_fyers_order_side(side: OrderSide) -> int:
    """Convert Nautilus order side to Fyers."""
    return 1 if side == OrderSide.BUY else -1


def parse_order_status(fyers_status: int) -> OrderStatus:
    """Convert Fyers order status to Nautilus."""
    mapping = {
        1: OrderStatus.CANCELED,
        2: OrderStatus.FILLED,
        3: OrderStatus.SUBMITTED,
        4: OrderStatus.REJECTED,
        5: OrderStatus.ACCEPTED,
        6: OrderStatus.EXPIRED,
        7: OrderStatus.PARTIALLY_FILLED,
    }
    return mapping.get(fyers_status, OrderStatus.INITIALIZED)


def parse_order_type(fyers_type: int) -> OrderType:
    """Convert Fyers order type to Nautilus."""
    mapping = {
        1: OrderType.LIMIT,
        2: OrderType.MARKET,
        3: OrderType.STOP_MARKET,
        4: OrderType.STOP_LIMIT,
    }
    return mapping.get(fyers_type, OrderType.LIMIT)


def to_fyers_order_type(order_type: OrderType) -> int:
    """Convert Nautilus order type to Fyers."""
    mapping = {
        OrderType.LIMIT: 1,
        OrderType.MARKET: 2,
        OrderType.STOP_MARKET: 3,
        OrderType.STOP_LIMIT: 4,
    }
    return mapping.get(order_type, 1)


def parse_time_in_force(fyers_validity: str) -> TimeInForce:
    """Convert Fyers validity to Nautilus TimeInForce."""
    return TimeInForce.IOC if fyers_validity == "IOC" else TimeInForce.DAY


def to_fyers_validity(tif: TimeInForce) -> str:
    """Convert Nautilus TimeInForce to Fyers validity."""
    return "IOC" if tif == TimeInForce.IOC else "DAY"


def parse_quote_tick(
    data: dict,
    instrument_id: InstrumentId,
    ts_init: int,
) -> QuoteTick:
    """Parse Fyers quote data to QuoteTick."""
    return QuoteTick(
        instrument_id=instrument_id,
        bid_price=Price.from_str(str(data.get("bid_price", data.get("bp", 0)))),
        ask_price=Price.from_str(str(data.get("ask_price", data.get("ap", 0)))),
        bid_size=Quantity.from_str(str(data.get("bid_qty", data.get("bq", 0)))),
        ask_size=Quantity.from_str(str(data.get("ask_qty", data.get("aq", 0)))),
        ts_event=millis_to_nanos(data.get("timestamp", 0)),
        ts_init=ts_init,
    )


def parse_trade_tick(
    data: dict,
    instrument_id: InstrumentId,
    ts_init: int,
) -> TradeTick:
    """Parse Fyers trade data to TradeTick."""
    return TradeTick(
        instrument_id=instrument_id,
        price=Price.from_str(str(data.get("lp", data.get("last_price", 0)))),
        size=Quantity.from_str(str(data.get("last_traded_qty", 1))),
        aggressor_side=AggressorSide.NO_AGGRESSOR,
        trade_id=TradeId(str(data.get("tt", 0))),  # trade time as ID
        ts_event=millis_to_nanos(data.get("timestamp", 0)),
        ts_init=ts_init,
    )


def parse_bar(
    candle: list,
    instrument_id: InstrumentId,
    bar_type: BarType,
    ts_init: int,
) -> Bar:
    """
    Parse Fyers candle data to Bar.

    Candle format: [timestamp, open, high, low, close, volume]
    """
    return Bar(
        bar_type=bar_type,
        open=Price.from_str(str(candle[1])),
        high=Price.from_str(str(candle[2])),
        low=Price.from_str(str(candle[3])),
        close=Price.from_str(str(candle[4])),
        volume=Quantity.from_str(str(candle[5])),
        ts_event=millis_to_nanos(candle[0] * 1000),  # Convert to ms
        ts_init=ts_init,
    )
```

### 8. Data Client (`data.py`)

```python
import asyncio
from nautilus_trader.cache.cache import Cache
from nautilus_trader.common.component import LiveClock, MessageBus
from nautilus_trader.live.data_client import LiveMarketDataClient
from nautilus_trader.model.data import Bar, BarType, QuoteTick, TradeTick
from nautilus_trader.model.identifiers import ClientId, InstrumentId

from .config import FyersDataClientConfig
from .constants import FYERS_VENUE
from .http.client import FyersHttpClient
from .websocket.client import FyersWebSocketClient
from .parsing import parse_quote_tick, parse_trade_tick, parse_bar
from .providers import FyersInstrumentProvider
from .symbol import to_fyers_symbol


class FyersDataClient(LiveMarketDataClient):
    """Live market data client for Fyers."""

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        client_id: ClientId,
        msgbus: MessageBus,
        cache: Cache,
        clock: LiveClock,
        instrument_provider: FyersInstrumentProvider,
        config: FyersDataClientConfig,
    ):
        super().__init__(
            loop=loop,
            client_id=client_id,
            venue=FYERS_VENUE,
            msgbus=msgbus,
            cache=cache,
            clock=clock,
            instrument_provider=instrument_provider,
        )

        self._config = config
        self._http_client = FyersHttpClient(
            client_id=config.client_id,
            access_token=config.access_token,
            base_url=config.base_url_http,
        )
        self._ws_client: FyersWebSocketClient | None = None
        self._subscribed_quotes: set[InstrumentId] = set()
        self._subscribed_trades: set[InstrumentId] = set()

    async def _connect(self) -> None:
        """Connect to Fyers."""
        await self._http_client.connect()

        # Initialize WebSocket
        self._ws_client = FyersWebSocketClient(
            client_id=self._config.client_id,
            access_token=self._config.access_token,
            on_message=self._handle_ws_message,
            on_error=self._handle_ws_error,
            ws_url=self._config.base_url_ws,
        )
        await self._ws_client.connect()

        # Load instruments
        if self._config.load_instruments_on_start:
            await self._instrument_provider.load_all_async()

    async def _disconnect(self) -> None:
        """Disconnect from Fyers."""
        if self._ws_client:
            await self._ws_client.disconnect()
        await self._http_client.disconnect()

    async def _subscribe_quote_ticks(self, instrument_id: InstrumentId) -> None:
        """Subscribe to quote ticks."""
        fyers_symbol = to_fyers_symbol(instrument_id)
        await self._ws_client.subscribe([fyers_symbol], data_type="depth")
        self._subscribed_quotes.add(instrument_id)

    async def _subscribe_trade_ticks(self, instrument_id: InstrumentId) -> None:
        """Subscribe to trade ticks."""
        fyers_symbol = to_fyers_symbol(instrument_id)
        await self._ws_client.subscribe([fyers_symbol], data_type="quote")
        self._subscribed_trades.add(instrument_id)

    async def _unsubscribe_quote_ticks(self, instrument_id: InstrumentId) -> None:
        """Unsubscribe from quote ticks."""
        fyers_symbol = to_fyers_symbol(instrument_id)
        await self._ws_client.unsubscribe([fyers_symbol])
        self._subscribed_quotes.discard(instrument_id)

    async def _unsubscribe_trade_ticks(self, instrument_id: InstrumentId) -> None:
        """Unsubscribe from trade ticks."""
        fyers_symbol = to_fyers_symbol(instrument_id)
        await self._ws_client.unsubscribe([fyers_symbol])
        self._subscribed_trades.discard(instrument_id)

    async def _request_bars(
        self,
        bar_type: BarType,
        limit: int,
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
        start_ts = start or (end_ts - limit * self._get_bar_seconds(bar_type))

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

        return bars

    def _handle_ws_message(self, data: dict) -> None:
        """Handle WebSocket message."""
        ts_init = self._clock.timestamp_ns()

        # Parse symbol
        symbol = data.get("symbol", data.get("n"))
        if not symbol:
            return

        instrument_id = self._get_instrument_id(symbol)
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

    def _handle_ws_error(self, error: Exception) -> None:
        """Handle WebSocket error."""
        self._log.error(f"WebSocket error: {error}")

    def _map_resolution(self, bar_type: BarType) -> str:
        """Map BarType to Fyers resolution string."""
        spec = bar_type.spec

        if spec.aggregation.value == "MINUTE":
            return str(spec.step)  # "1", "5", "15", etc.
        elif spec.aggregation.value == "HOUR":
            return str(spec.step * 60)  # Convert to minutes
        elif spec.aggregation.value == "DAY":
            return "D"
        elif spec.aggregation.value == "WEEK":
            return "W"
        elif spec.aggregation.value == "MONTH":
            return "M"

        return "1"  # Default to 1 minute

    def _get_bar_seconds(self, bar_type: BarType) -> int:
        """Get number of seconds per bar."""
        spec = bar_type.spec

        multipliers = {
            "MINUTE": 60,
            "HOUR": 3600,
            "DAY": 86400,
            "WEEK": 604800,
        }

        return multipliers.get(spec.aggregation.value, 60) * spec.step

    def _get_instrument_id(self, fyers_symbol: str) -> InstrumentId | None:
        """Get InstrumentId from Fyers symbol."""
        from .symbol import parse_fyers_symbol
        return parse_fyers_symbol(fyers_symbol)
```

### 9. Execution Client (`execution.py`)

```python
import asyncio
from decimal import Decimal
from nautilus_trader.cache.cache import Cache
from nautilus_trader.common.component import LiveClock, MessageBus
from nautilus_trader.execution.messages import (
    CancelOrder, ModifyOrder, SubmitOrder, SubmitOrderList,
)
from nautilus_trader.live.execution_client import LiveExecutionClient
from nautilus_trader.model.enums import OmsType, AccountType, OrderStatus
from nautilus_trader.model.events import (
    OrderAccepted, OrderCanceled, OrderFilled, OrderRejected, OrderSubmitted,
)
from nautilus_trader.model.identifiers import (
    AccountId, ClientId, ClientOrderId, InstrumentId, VenueOrderId,
)
from nautilus_trader.model.objects import Money, Price, Quantity
from nautilus_trader.model.orders import Order

from .config import FyersExecClientConfig
from .constants import FYERS_VENUE
from .http.client import FyersHttpClient, FyersApiError
from .parsing import (
    to_fyers_order_side, to_fyers_order_type, to_fyers_validity,
    parse_order_status,
)
from .symbol import to_fyers_symbol


class FyersExecutionClient(LiveExecutionClient):
    """Live execution client for Fyers."""

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        client_id: ClientId,
        msgbus: MessageBus,
        cache: Cache,
        clock: LiveClock,
        config: FyersExecClientConfig,
    ):
        super().__init__(
            loop=loop,
            client_id=client_id,
            venue=FYERS_VENUE,
            oms_type=OmsType.NETTING,
            account_type=AccountType.MARGIN,
            base_currency=None,  # INR
            msgbus=msgbus,
            cache=cache,
            clock=clock,
        )

        self._config = config
        self._http_client = FyersHttpClient(
            client_id=config.client_id,
            access_token=config.access_token,
            base_url=config.base_url_http,
        )

        # Order ID mapping
        self._order_ids: dict[ClientOrderId, VenueOrderId] = {}
        self._venue_order_ids: dict[VenueOrderId, ClientOrderId] = {}

    async def _connect(self) -> None:
        """Connect to Fyers."""
        await self._http_client.connect()

        # Get account info
        profile = await self._http_client.get_profile()
        self._log.info(f"Connected as {profile.get('data', {}).get('name', 'Unknown')}")

    async def _disconnect(self) -> None:
        """Disconnect from Fyers."""
        await self._http_client.disconnect()

    async def _submit_order(self, command: SubmitOrder) -> None:
        """Submit an order to Fyers."""
        order = command.order

        # Build Fyers order request
        fyers_order = {
            "symbol": to_fyers_symbol(order.instrument_id),
            "qty": int(order.quantity),
            "type": to_fyers_order_type(order.order_type),
            "side": to_fyers_order_side(order.side),
            "productType": self._config.default_product_type,
            "validity": to_fyers_validity(order.time_in_force),
            "disclosedQty": 0,
            "offlineOrder": False,
        }

        # Add price for limit orders
        if order.price:
            fyers_order["limitPrice"] = float(order.price)

        # Add trigger price for stop orders
        if order.trigger_price:
            fyers_order["stopPrice"] = float(order.trigger_price)

        try:
            # Submit order
            response = await self._http_client.place_order(fyers_order)

            venue_order_id = VenueOrderId(str(response.get("id")))
            self._order_ids[order.client_order_id] = venue_order_id
            self._venue_order_ids[venue_order_id] = order.client_order_id

            # Generate submitted event
            self.generate_order_submitted(
                strategy_id=order.strategy_id,
                instrument_id=order.instrument_id,
                client_order_id=order.client_order_id,
                ts_event=self._clock.timestamp_ns(),
            )

            # Generate accepted event
            self.generate_order_accepted(
                strategy_id=order.strategy_id,
                instrument_id=order.instrument_id,
                client_order_id=order.client_order_id,
                venue_order_id=venue_order_id,
                ts_event=self._clock.timestamp_ns(),
            )

        except FyersApiError as e:
            self.generate_order_rejected(
                strategy_id=order.strategy_id,
                instrument_id=order.instrument_id,
                client_order_id=order.client_order_id,
                reason=e.message,
                ts_event=self._clock.timestamp_ns(),
            )

    async def _cancel_order(self, command: CancelOrder) -> None:
        """Cancel an order."""
        venue_order_id = self._order_ids.get(command.client_order_id)

        if not venue_order_id:
            self._log.error(f"No venue order ID for {command.client_order_id}")
            return

        try:
            await self._http_client.cancel_order(str(venue_order_id))

            self.generate_order_canceled(
                strategy_id=command.strategy_id,
                instrument_id=command.instrument_id,
                client_order_id=command.client_order_id,
                venue_order_id=venue_order_id,
                ts_event=self._clock.timestamp_ns(),
            )

        except FyersApiError as e:
            self._log.error(f"Cancel failed: {e.message}")

    async def _modify_order(self, command: ModifyOrder) -> None:
        """Modify an existing order."""
        venue_order_id = self._order_ids.get(command.client_order_id)

        if not venue_order_id:
            self._log.error(f"No venue order ID for {command.client_order_id}")
            return

        updates = {"id": str(venue_order_id)}

        if command.quantity:
            updates["qty"] = int(command.quantity)
        if command.price:
            updates["limitPrice"] = float(command.price)
        if command.trigger_price:
            updates["stopPrice"] = float(command.trigger_price)

        try:
            await self._http_client.modify_order(str(venue_order_id), updates)

            self.generate_order_updated(
                strategy_id=command.strategy_id,
                instrument_id=command.instrument_id,
                client_order_id=command.client_order_id,
                venue_order_id=venue_order_id,
                quantity=command.quantity,
                price=command.price,
                trigger_price=command.trigger_price,
                ts_event=self._clock.timestamp_ns(),
            )

        except FyersApiError as e:
            self._log.error(f"Modify failed: {e.message}")

    async def generate_order_status_report(
        self,
        instrument_id: InstrumentId,
        client_order_id: ClientOrderId,
        venue_order_id: VenueOrderId,
    ):
        """Generate order status report from Fyers."""
        try:
            response = await self._http_client.get_order(str(venue_order_id))
            order_data = response.get("orderBook", [{}])[0]

            return self._parse_order_report(order_data, instrument_id, client_order_id)

        except FyersApiError as e:
            self._log.error(f"Failed to get order status: {e.message}")
            return None

    async def generate_fill_reports(
        self,
        instrument_id: InstrumentId,
        venue_order_id: VenueOrderId,
    ):
        """Generate fill reports for an order."""
        # Fyers combines order and fill info in order response
        return []

    async def generate_position_status_reports(self):
        """Generate position status reports."""
        try:
            response = await self._http_client.get_positions()

            reports = []
            for pos in response.get("netPositions", []):
                # Parse position data
                pass

            return reports

        except FyersApiError as e:
            self._log.error(f"Failed to get positions: {e.message}")
            return []
```

### 10. Instrument Provider (`providers.py`)

```python
import csv
import io
import aiohttp
from nautilus_trader.common.providers import InstrumentProvider
from nautilus_trader.model.identifiers import InstrumentId, Symbol
from nautilus_trader.model.instruments import (
    Equity, CurrencyPair, Future, Option, Instrument,
)
from nautilus_trader.model.objects import Price, Quantity, Money
from nautilus_trader.model.currencies import INR

from .config import FyersInstrumentProviderConfig
from .constants import (
    FYERS_VENUE,
    SYMBOL_MASTER_NSE_CM, SYMBOL_MASTER_NSE_FO,
    SYMBOL_MASTER_BSE_CM, SYMBOL_MASTER_MCX,
)


class FyersInstrumentProvider(InstrumentProvider):
    """Instrument provider for Fyers."""

    def __init__(self, config: FyersInstrumentProviderConfig):
        super().__init__()
        self._config = config
        self._instruments: dict[InstrumentId, Instrument] = {}

    async def load_all_async(self, filters: dict | None = None) -> None:
        """Load all instruments from Fyers symbol master."""
        async with aiohttp.ClientSession() as session:
            for segment in self._config.segments:
                url = self._get_symbol_master_url(segment)
                await self._load_segment(session, url, segment)

    async def _load_segment(
        self,
        session: aiohttp.ClientSession,
        url: str,
        segment: str,
    ) -> None:
        """Load instruments from a symbol master CSV."""
        async with session.get(url) as response:
            if response.status != 200:
                return

            content = await response.text()
            reader = csv.DictReader(io.StringIO(content))

            for row in reader:
                try:
                    instrument = self._parse_instrument(row, segment)
                    if instrument:
                        self._instruments[instrument.id] = instrument
                        self.add(instrument)
                except Exception as e:
                    continue

    def _parse_instrument(self, row: dict, segment: str) -> Instrument | None:
        """Parse CSV row to Instrument."""
        symbol = row.get("symbol", row.get("Symbol", ""))

        if not symbol:
            return None

        instrument_id = InstrumentId(Symbol(symbol), FYERS_VENUE)

        # Determine instrument type based on segment
        if segment in ("NSE_CM", "BSE_CM"):
            return self._create_equity(row, instrument_id)
        elif "FO" in segment:
            if "CE" in symbol or "PE" in symbol:
                return self._create_option(row, instrument_id)
            elif "FUT" in symbol:
                return self._create_future(row, instrument_id)

        return self._create_equity(row, instrument_id)

    def _create_equity(self, row: dict, instrument_id: InstrumentId) -> Equity:
        """Create Equity instrument."""
        tick_size = float(row.get("tick_size", row.get("Tick Size", 0.05)))
        lot_size = int(row.get("lot_size", row.get("Lot Size", 1)))

        return Equity(
            instrument_id=instrument_id,
            raw_symbol=Symbol(instrument_id.symbol.value),
            currency=INR,
            price_precision=2,
            price_increment=Price.from_str(str(tick_size)),
            lot_size=Quantity.from_int(lot_size),
            ts_event=0,
            ts_init=0,
        )

    def _create_future(self, row: dict, instrument_id: InstrumentId) -> Future:
        """Create Future instrument."""
        tick_size = float(row.get("tick_size", 0.05))
        lot_size = int(row.get("lot_size", 1))
        expiry = row.get("expiry", "")

        return Future(
            instrument_id=instrument_id,
            raw_symbol=Symbol(instrument_id.symbol.value),
            asset_class=AssetClass.INDEX,  # or EQUITY
            currency=INR,
            price_precision=2,
            price_increment=Price.from_str(str(tick_size)),
            multiplier=Quantity.from_int(lot_size),
            lot_size=Quantity.from_int(lot_size),
            underlying=instrument_id.symbol.value.split("25")[0],  # Extract underlying
            expiry_date=expiry,
            ts_event=0,
            ts_init=0,
        )

    def _create_option(self, row: dict, instrument_id: InstrumentId) -> Option:
        """Create Option instrument."""
        tick_size = float(row.get("tick_size", 0.05))
        lot_size = int(row.get("lot_size", 1))

        # Parse option details from symbol
        from .symbol import parse_option_symbol
        details = parse_option_symbol(instrument_id.symbol.value)

        return Option(
            instrument_id=instrument_id,
            raw_symbol=Symbol(instrument_id.symbol.value),
            asset_class=AssetClass.INDEX,
            currency=INR,
            price_precision=2,
            price_increment=Price.from_str(str(tick_size)),
            multiplier=Quantity.from_int(lot_size),
            lot_size=Quantity.from_int(lot_size),
            underlying=details["underlying"] if details else "",
            strike_price=Price.from_int(details["strike"]) if details else Price.from_int(0),
            option_kind=OptionKind.CALL if details and details["option_type"] == "CE" else OptionKind.PUT,
            ts_event=0,
            ts_init=0,
        )

    def _get_symbol_master_url(self, segment: str) -> str:
        """Get symbol master URL for segment."""
        urls = {
            "NSE_CM": SYMBOL_MASTER_NSE_CM,
            "NSE_FO": SYMBOL_MASTER_NSE_FO,
            "BSE_CM": SYMBOL_MASTER_BSE_CM,
            "MCX_COM": SYMBOL_MASTER_MCX,
        }
        return urls.get(segment, SYMBOL_MASTER_NSE_CM)
```

---

## Testing Strategy

### Unit Tests

```python
# tests/unit/adapters/fyers/test_parsing.py
import pytest
from nautilus_trader.adapters.fyers.parsing import (
    parse_order_side, parse_order_status, parse_quote_tick,
)
from nautilus_trader.model.enums import OrderSide, OrderStatus

class TestFyersParsing:
    def test_parse_order_side_buy(self):
        assert parse_order_side(1) == OrderSide.BUY

    def test_parse_order_side_sell(self):
        assert parse_order_side(-1) == OrderSide.SELL

    def test_parse_order_status_filled(self):
        assert parse_order_status(2) == OrderStatus.FILLED

    def test_parse_order_status_pending(self):
        assert parse_order_status(5) == OrderStatus.ACCEPTED
```

### Integration Tests

```python
# tests/integration/adapters/fyers/test_http_client.py
import pytest
from nautilus_trader.adapters.fyers.http.client import FyersHttpClient

@pytest.mark.asyncio
async def test_get_market_status():
    client = FyersHttpClient(
        client_id="TEST-100",
        access_token="test_token",
    )
    await client.connect()

    # This will fail with invalid token but tests connectivity
    with pytest.raises(Exception):
        await client.get_market_status()

    await client.disconnect()
```

### Mock Server for Testing

```python
# tests/mocks/fyers_mock_server.py
from aiohttp import web

async def mock_profile(request):
    return web.json_response({
        "s": "ok",
        "data": {
            "fy_id": "TEST123",
            "name": "Test User",
        }
    })

async def mock_orders(request):
    return web.json_response({
        "s": "ok",
        "orderBook": []
    })

def create_mock_app():
    app = web.Application()
    app.router.add_get("/api/v3/profile", mock_profile)
    app.router.add_get("/api/v3/orders", mock_orders)
    return app
```

---

## Usage Example

```python
from nautilus_trader.adapters.fyers import (
    FYERS_VENUE,
    FyersDataClientConfig,
    FyersExecClientConfig,
    FyersLiveDataClientFactory,
    FyersLiveExecClientFactory,
)
from nautilus_trader.live.node import TradingNode

# Configuration
data_config = FyersDataClientConfig(
    client_id="XXXXXX-100",
    access_token="your_access_token",
    instrument_segments=["NSE_CM", "NSE_FO"],
)

exec_config = FyersExecClientConfig(
    client_id="XXXXXX-100",
    access_token="your_access_token",
    default_product_type="INTRADAY",
)

# Create trading node
node = TradingNode()

# Add Fyers clients
node.add_data_client_factory(FYERS_VENUE, FyersLiveDataClientFactory)
node.add_exec_client_factory(FYERS_VENUE, FyersLiveExecClientFactory)

# Configure and run
node.add_data_client(data_config)
node.add_exec_client(exec_config)

# Add your strategy
node.add_strategy(YourStrategy(config))

node.run()
```

---

## References

- [Fyers API Portal](https://myapi.fyers.in/)
- [Fyers API Documentation](https://myapi.fyers.in/docsv3)
- [Fyers Python SDK (PyPI)](https://pypi.org/project/fyers-apiv3/)
- [GitHub - fyers-api-access-token-v3](https://github.com/tkanhe/fyers-api-access-token-v3)
- [GitHub - extra-fyers](https://github.com/nodef/extra-fyers)
- [GitHub - fyers-websockets](https://github.com/marketcalls/fyers-websockets)

---

## Notes for Implementation

1. **Daily Token Refresh**: Fyers tokens expire at 3:00 AM IST daily (SEBI requirement). Implement automatic token refresh or manual re-authentication.

2. **Rate Limiting**: Respect the 100,000 requests/day limit. Implement request queuing and rate limiting.

3. **Market Hours**: NSE trading hours are 9:15 AM - 3:30 PM IST. Handle pre-market and post-market sessions appropriately.

4. **Symbol Master**: Download and cache the symbol master CSV files for efficient symbol lookup.

5. **Order Types**: Fyers supports Market, Limit, Stop-Loss Market (SL-M), and Stop-Loss Limit (SL-L). Map NautilusTrader order types accordingly.

6. **Product Types**: Handle CNC (delivery), INTRADAY (MIS), MARGIN, CO (Cover Order), and BO (Bracket Order) correctly.

7. **Testing**: Use Fyers paper trading or testnet if available. Always test with small quantities first.
