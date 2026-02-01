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
Fyers type conversion and parsing utilities.
"""

from typing import Any

from nautilus_trader.adapters.fyers.constants import FYERS_VENUE
from nautilus_trader.adapters.fyers.enums import FyersOrderSide
from nautilus_trader.adapters.fyers.enums import FyersOrderStatus
from nautilus_trader.adapters.fyers.enums import FyersOrderType
from nautilus_trader.adapters.fyers.enums import FyersProductType
from nautilus_trader.adapters.fyers.enums import FyersValidity
from nautilus_trader.adapters.fyers.symbol import parse_fyers_symbol
from nautilus_trader.core.datetime import millis_to_nanos
from nautilus_trader.core.datetime import secs_to_nanos
from nautilus_trader.core.uuid import UUID4
from nautilus_trader.model.data import Bar
from nautilus_trader.model.data import BarType
from nautilus_trader.model.data import QuoteTick
from nautilus_trader.model.data import TradeTick
from nautilus_trader.model.enums import AggressorSide
from nautilus_trader.model.enums import OrderSide
from nautilus_trader.model.enums import OrderStatus
from nautilus_trader.model.enums import OrderType
from nautilus_trader.model.enums import TimeInForce
from nautilus_trader.model.identifiers import AccountId
from nautilus_trader.model.identifiers import ClientOrderId
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.identifiers import TradeId
from nautilus_trader.model.identifiers import VenueOrderId
from nautilus_trader.model.objects import Price
from nautilus_trader.model.objects import Quantity


# -----------------------------------------------------------------------------
# Order side conversions
# -----------------------------------------------------------------------------


def parse_order_side(fyers_side: int) -> OrderSide:
    """
    Convert Fyers order side to Nautilus OrderSide.

    Parameters
    ----------
    fyers_side : int
        The Fyers order side (1=BUY, -1=SELL).

    Returns
    -------
    OrderSide

    """
    return OrderSide.BUY if fyers_side == 1 else OrderSide.SELL


def to_fyers_order_side(side: OrderSide) -> int:
    """
    Convert Nautilus OrderSide to Fyers order side.

    Parameters
    ----------
    side : OrderSide
        The Nautilus order side.

    Returns
    -------
    int
        The Fyers order side (1=BUY, -1=SELL).

    """
    return 1 if side == OrderSide.BUY else -1


# -----------------------------------------------------------------------------
# Order status conversions
# -----------------------------------------------------------------------------


def parse_order_status(fyers_status: int) -> OrderStatus:
    """
    Convert Fyers order status to Nautilus OrderStatus.

    Parameters
    ----------
    fyers_status : int
        The Fyers order status code.

    Returns
    -------
    OrderStatus

    """
    mapping = {
        FyersOrderStatus.CANCELLED: OrderStatus.CANCELED,
        FyersOrderStatus.TRADED: OrderStatus.FILLED,
        FyersOrderStatus.TRANSIT: OrderStatus.SUBMITTED,
        FyersOrderStatus.REJECTED: OrderStatus.REJECTED,
        FyersOrderStatus.PENDING: OrderStatus.ACCEPTED,
        FyersOrderStatus.EXPIRED: OrderStatus.EXPIRED,
        FyersOrderStatus.PARTIALLY_FILLED: OrderStatus.PARTIALLY_FILLED,
    }
    return mapping.get(fyers_status, OrderStatus.INITIALIZED)


# -----------------------------------------------------------------------------
# Order type conversions
# -----------------------------------------------------------------------------


def parse_order_type(fyers_type: int) -> OrderType:
    """
    Convert Fyers order type to Nautilus OrderType.

    Parameters
    ----------
    fyers_type : int
        The Fyers order type code.

    Returns
    -------
    OrderType

    """
    mapping = {
        FyersOrderType.LIMIT: OrderType.LIMIT,
        FyersOrderType.MARKET: OrderType.MARKET,
        FyersOrderType.STOP_LOSS_MARKET: OrderType.STOP_MARKET,
        FyersOrderType.STOP_LOSS_LIMIT: OrderType.STOP_LIMIT,
    }
    return mapping.get(fyers_type, OrderType.LIMIT)


def to_fyers_order_type(order_type: OrderType) -> int:
    """
    Convert Nautilus OrderType to Fyers order type.

    Parameters
    ----------
    order_type : OrderType
        The Nautilus order type.

    Returns
    -------
    int
        The Fyers order type code.

    """
    mapping = {
        OrderType.LIMIT: FyersOrderType.LIMIT,
        OrderType.MARKET: FyersOrderType.MARKET,
        OrderType.STOP_MARKET: FyersOrderType.STOP_LOSS_MARKET,
        OrderType.STOP_LIMIT: FyersOrderType.STOP_LOSS_LIMIT,
    }
    return mapping.get(order_type, FyersOrderType.LIMIT)


# -----------------------------------------------------------------------------
# Time in force conversions
# -----------------------------------------------------------------------------


def parse_time_in_force(fyers_validity: str) -> TimeInForce:
    """
    Convert Fyers validity to Nautilus TimeInForce.

    Parameters
    ----------
    fyers_validity : str
        The Fyers validity string.

    Returns
    -------
    TimeInForce

    """
    if fyers_validity == FyersValidity.IOC:
        return TimeInForce.IOC
    return TimeInForce.DAY


def to_fyers_validity(tif: TimeInForce) -> str:
    """
    Convert Nautilus TimeInForce to Fyers validity.

    Parameters
    ----------
    tif : TimeInForce
        The Nautilus time in force.

    Returns
    -------
    str
        The Fyers validity string.

    """
    if tif == TimeInForce.IOC:
        return FyersValidity.IOC
    return FyersValidity.DAY


# -----------------------------------------------------------------------------
# Market data parsing
# -----------------------------------------------------------------------------


def parse_quote_tick(
    data: dict[str, Any],
    instrument_id: InstrumentId,
    ts_init: int,
) -> QuoteTick:
    """
    Parse Fyers quote data to QuoteTick.

    Parameters
    ----------
    data : dict
        The Fyers quote data.
    instrument_id : InstrumentId
        The instrument ID.
    ts_init : int
        The initialization timestamp (nanoseconds).

    Returns
    -------
    QuoteTick

    """
    # Handle both REST and WebSocket data formats
    bid_price = data.get("bid_price", data.get("bp", 0))
    ask_price = data.get("ask_price", data.get("ap", 0))
    bid_size = data.get("bid_qty", data.get("bq", 0))
    ask_size = data.get("ask_qty", data.get("aq", 0))
    timestamp = data.get("timestamp", data.get("tt", 0))

    # Convert timestamp (seconds or milliseconds to nanoseconds)
    if timestamp > 1e12:  # Milliseconds
        ts_event = millis_to_nanos(timestamp)
    else:  # Seconds
        ts_event = secs_to_nanos(timestamp)

    return QuoteTick(
        instrument_id=instrument_id,
        bid_price=Price.from_str(str(bid_price)),
        ask_price=Price.from_str(str(ask_price)),
        bid_size=Quantity.from_str(str(max(bid_size, 0))),
        ask_size=Quantity.from_str(str(max(ask_size, 0))),
        ts_event=ts_event,
        ts_init=ts_init,
    )


def parse_trade_tick(
    data: dict[str, Any],
    instrument_id: InstrumentId,
    ts_init: int,
) -> TradeTick:
    """
    Parse Fyers trade data to TradeTick.

    Parameters
    ----------
    data : dict
        The Fyers trade data.
    instrument_id : InstrumentId
        The instrument ID.
    ts_init : int
        The initialization timestamp (nanoseconds).

    Returns
    -------
    TradeTick

    """
    # Handle both REST and WebSocket data formats
    last_price = data.get("lp", data.get("last_price", data.get("ltp", 0)))
    last_qty = data.get("last_traded_qty", data.get("ltq", 1))
    timestamp = data.get("timestamp", data.get("tt", 0))

    # Convert timestamp
    if timestamp > 1e12:  # Milliseconds
        ts_event = millis_to_nanos(timestamp)
    else:  # Seconds
        ts_event = secs_to_nanos(timestamp)

    # Generate trade ID from timestamp if not provided
    trade_id = str(data.get("trade_id", timestamp))

    return TradeTick(
        instrument_id=instrument_id,
        price=Price.from_str(str(last_price)),
        size=Quantity.from_str(str(max(last_qty, 1))),
        aggressor_side=AggressorSide.NO_AGGRESSOR,
        trade_id=TradeId(trade_id),
        ts_event=ts_event,
        ts_init=ts_init,
    )


def parse_bar(
    candle: list[Any],
    instrument_id: InstrumentId,
    bar_type: BarType,
    ts_init: int,
) -> Bar:
    """
    Parse Fyers candle data to Bar.

    Parameters
    ----------
    candle : list
        The candle data [timestamp, open, high, low, close, volume].
    instrument_id : InstrumentId
        The instrument ID.
    bar_type : BarType
        The bar type.
    ts_init : int
        The initialization timestamp (nanoseconds).

    Returns
    -------
    Bar

    """
    # Fyers candle format: [timestamp, open, high, low, close, volume]
    timestamp = candle[0]
    open_price = candle[1]
    high_price = candle[2]
    low_price = candle[3]
    close_price = candle[4]
    volume = candle[5]

    # Convert timestamp (seconds to nanoseconds)
    ts_event = secs_to_nanos(timestamp)

    return Bar(
        bar_type=bar_type,
        open=Price.from_str(str(open_price)),
        high=Price.from_str(str(high_price)),
        low=Price.from_str(str(low_price)),
        close=Price.from_str(str(close_price)),
        volume=Quantity.from_str(str(volume)),
        ts_event=ts_event,
        ts_init=ts_init,
    )


# -----------------------------------------------------------------------------
# Order parsing
# -----------------------------------------------------------------------------


def parse_order_response(
    data: dict[str, Any],
    instrument_id: InstrumentId,
    client_order_id: ClientOrderId,
) -> dict[str, Any]:
    """
    Parse Fyers order response data.

    Parameters
    ----------
    data : dict
        The Fyers order data.
    instrument_id : InstrumentId
        The instrument ID.
    client_order_id : ClientOrderId
        The client order ID.

    Returns
    -------
    dict
        Parsed order information.

    """
    return {
        "instrument_id": instrument_id,
        "client_order_id": client_order_id,
        "venue_order_id": VenueOrderId(str(data.get("id", data.get("orderId", "")))),
        "order_side": parse_order_side(data.get("side", 1)),
        "order_type": parse_order_type(data.get("type", 1)),
        "order_status": parse_order_status(data.get("status", 5)),
        "quantity": Quantity.from_str(str(data.get("qty", 0))),
        "filled_qty": Quantity.from_str(str(data.get("filledQty", data.get("tradedQty", 0)))),
        "price": Price.from_str(str(data.get("limitPrice", 0))) if data.get("limitPrice") else None,
        "trigger_price": Price.from_str(str(data.get("stopPrice", 0))) if data.get("stopPrice") else None,
        "avg_price": Price.from_str(str(data.get("avgPrice", data.get("tradedPrice", 0)))),
        "time_in_force": parse_time_in_force(data.get("validity", "DAY")),
        "message": data.get("message", ""),
    }


# -----------------------------------------------------------------------------
# Position parsing
# -----------------------------------------------------------------------------


def parse_position(data: dict[str, Any]) -> dict[str, Any]:
    """
    Parse Fyers position data.

    Parameters
    ----------
    data : dict
        The Fyers position data.

    Returns
    -------
    dict
        Parsed position information.

    """
    symbol = data.get("symbol", "")
    instrument_id = parse_fyers_symbol(symbol)

    net_qty = data.get("netQty", data.get("qty", 0))
    buy_qty = data.get("buyQty", 0)
    sell_qty = data.get("sellQty", 0)
    buy_avg = data.get("buyAvgPrice", data.get("buyAvg", 0))
    sell_avg = data.get("sellAvgPrice", data.get("sellAvg", 0))

    return {
        "instrument_id": instrument_id,
        "symbol": symbol,
        "net_qty": net_qty,
        "buy_qty": buy_qty,
        "sell_qty": sell_qty,
        "buy_avg": buy_avg,
        "sell_avg": sell_avg,
        "realized_pnl": data.get("realizedProfit", data.get("realized_profit", 0)),
        "unrealized_pnl": data.get("unrealizedProfit", data.get("unrealized_profit", 0)),
        "product_type": data.get("productType", "INTRADAY"),
    }


# -----------------------------------------------------------------------------
# Account parsing
# -----------------------------------------------------------------------------


def parse_account_balance(data: dict[str, Any], fyers_id: str) -> dict[str, Any]:
    """
    Parse Fyers funds/balance data.

    Parameters
    ----------
    data : dict
        The Fyers funds data.
    fyers_id : str
        The Fyers client ID.

    Returns
    -------
    dict
        Parsed account balance information.

    """
    fund_limit = data.get("fund_limit", [{}])
    if isinstance(fund_limit, list) and len(fund_limit) > 0:
        funds = fund_limit[0]
    else:
        funds = fund_limit if isinstance(fund_limit, dict) else {}

    return {
        "account_id": AccountId(f"{FYERS_VENUE.value}-{fyers_id}"),
        "total_balance": funds.get("total", funds.get("equityAmount", 0)),
        "available_balance": funds.get("available", funds.get("availableMargin", 0)),
        "used_margin": funds.get("utilized", funds.get("utilizedMargin", 0)),
        "currency": "INR",
    }
