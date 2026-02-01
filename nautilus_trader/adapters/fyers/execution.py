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
Fyers live execution client.
"""

import asyncio
from typing import Any

from nautilus_trader.adapters.fyers.config import FyersExecClientConfig
from nautilus_trader.adapters.fyers.constants import FYERS_VENUE
from nautilus_trader.adapters.fyers.http.client import FyersHttpClient
from nautilus_trader.adapters.fyers.http.error import FyersApiError
from nautilus_trader.adapters.fyers.parsing import parse_order_response
from nautilus_trader.adapters.fyers.parsing import parse_order_status
from nautilus_trader.adapters.fyers.parsing import parse_position
from nautilus_trader.adapters.fyers.parsing import to_fyers_order_side
from nautilus_trader.adapters.fyers.parsing import to_fyers_order_type
from nautilus_trader.adapters.fyers.parsing import to_fyers_validity
from nautilus_trader.adapters.fyers.symbol import to_fyers_symbol
from nautilus_trader.cache.cache import Cache
from nautilus_trader.common.component import LiveClock
from nautilus_trader.common.component import MessageBus
from nautilus_trader.core.correctness import PyCondition
from nautilus_trader.core.uuid import UUID4
from nautilus_trader.execution.messages import BatchCancelOrders
from nautilus_trader.execution.messages import CancelAllOrders
from nautilus_trader.execution.messages import CancelOrder
from nautilus_trader.execution.messages import GenerateFillReports
from nautilus_trader.execution.messages import GenerateOrderStatusReport
from nautilus_trader.execution.messages import GenerateOrderStatusReports
from nautilus_trader.execution.messages import GeneratePositionStatusReports
from nautilus_trader.execution.messages import ModifyOrder
from nautilus_trader.execution.messages import SubmitOrder
from nautilus_trader.execution.messages import SubmitOrderList
from nautilus_trader.execution.reports import FillReport
from nautilus_trader.execution.reports import OrderStatusReport
from nautilus_trader.execution.reports import PositionStatusReport
from nautilus_trader.live.execution_client import LiveExecutionClient
from nautilus_trader.model.enums import AccountType
from nautilus_trader.model.enums import LiquiditySide
from nautilus_trader.model.enums import OmsType
from nautilus_trader.model.enums import OrderSide
from nautilus_trader.model.enums import OrderStatus
from nautilus_trader.model.enums import OrderType
from nautilus_trader.model.enums import PositionSide
from nautilus_trader.model.identifiers import AccountId
from nautilus_trader.model.identifiers import ClientId
from nautilus_trader.model.identifiers import ClientOrderId
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.identifiers import PositionId
from nautilus_trader.model.identifiers import TradeId
from nautilus_trader.model.identifiers import VenueOrderId
from nautilus_trader.model.objects import Money
from nautilus_trader.model.objects import Price
from nautilus_trader.model.objects import Quantity
from nautilus_trader.model.orders import Order


class FyersExecutionClient(LiveExecutionClient):
    """
    Live execution client for Fyers.

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
    config : FyersExecClientConfig
        The client configuration.

    """

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        client_id: ClientId,
        msgbus: MessageBus,
        cache: Cache,
        clock: LiveClock,
        config: FyersExecClientConfig,
    ) -> None:
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

        PyCondition.not_none(config.client_id, "config.client_id")
        PyCondition.not_none(config.access_token, "config.access_token")

        self._config = config
        self._fyers_id = config.client_id.split("-")[0] if config.client_id else ""

        # HTTP client
        self._http_client = FyersHttpClient(
            client_id=config.client_id,
            access_token=config.access_token,
            base_url=config.base_url_http,
            logger=self._log,
        )

        # Order ID mappings
        self._order_ids: dict[ClientOrderId, VenueOrderId] = {}
        self._venue_order_ids: dict[VenueOrderId, ClientOrderId] = {}

        # Account ID
        self._account_id = AccountId(f"{FYERS_VENUE.value}-{self._fyers_id}")

    async def _connect(self) -> None:
        """Connect to Fyers."""
        self._log.info("Connecting to Fyers execution...")

        await self._http_client.connect()

        # Get profile to verify connection
        try:
            profile = await self._http_client.get_profile()
            name = profile.get("data", {}).get("name", "Unknown")
            self._log.info(f"Connected as {name}")
        except FyersApiError as e:
            self._log.error(f"Failed to get profile: {e}")
            raise

        self._log.info("Connected to Fyers execution")

    async def _disconnect(self) -> None:
        """Disconnect from Fyers."""
        self._log.info("Disconnecting from Fyers execution...")

        await self._http_client.disconnect()

        self._order_ids.clear()
        self._venue_order_ids.clear()

        self._log.info("Disconnected from Fyers execution")

    # -------------------------------------------------------------------------
    # Order submission
    # -------------------------------------------------------------------------

    async def _submit_order(self, command: SubmitOrder) -> None:
        """Submit an order to Fyers."""
        order = command.order

        # Build Fyers order request
        fyers_order = self._build_order_request(order)

        try:
            response = await self._http_client.place_order(fyers_order)

            # Extract order ID
            order_id = response.get("id", response.get("data", {}).get("id", ""))
            venue_order_id = VenueOrderId(str(order_id))

            # Store mapping
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

            self._log.info(f"Order submitted: {order.client_order_id} -> {venue_order_id}")

        except FyersApiError as e:
            self._log.error(f"Order submission failed: {e}")
            self.generate_order_rejected(
                strategy_id=order.strategy_id,
                instrument_id=order.instrument_id,
                client_order_id=order.client_order_id,
                reason=e.message,
                ts_event=self._clock.timestamp_ns(),
            )

    async def _submit_order_list(self, command: SubmitOrderList) -> None:
        """Submit an order list to Fyers."""
        # Fyers supports multi-order placement up to 10 orders
        orders = command.order_list.orders

        if len(orders) > 10:
            self._log.error("Fyers supports maximum 10 orders per batch")
            return

        fyers_orders = [self._build_order_request(order) for order in orders]

        try:
            response = await self._http_client.place_multi_order(fyers_orders)

            # Process responses for each order
            order_responses = response.get("data", [])
            for i, order in enumerate(orders):
                if i < len(order_responses):
                    order_resp = order_responses[i]
                    if order_resp.get("s") == "ok":
                        venue_order_id = VenueOrderId(str(order_resp.get("id", "")))
                        self._order_ids[order.client_order_id] = venue_order_id
                        self._venue_order_ids[venue_order_id] = order.client_order_id

                        self.generate_order_submitted(
                            strategy_id=order.strategy_id,
                            instrument_id=order.instrument_id,
                            client_order_id=order.client_order_id,
                            ts_event=self._clock.timestamp_ns(),
                        )
                        self.generate_order_accepted(
                            strategy_id=order.strategy_id,
                            instrument_id=order.instrument_id,
                            client_order_id=order.client_order_id,
                            venue_order_id=venue_order_id,
                            ts_event=self._clock.timestamp_ns(),
                        )
                    else:
                        self.generate_order_rejected(
                            strategy_id=order.strategy_id,
                            instrument_id=order.instrument_id,
                            client_order_id=order.client_order_id,
                            reason=order_resp.get("message", "Unknown error"),
                            ts_event=self._clock.timestamp_ns(),
                        )

        except FyersApiError as e:
            self._log.error(f"Multi-order submission failed: {e}")
            for order in orders:
                self.generate_order_rejected(
                    strategy_id=order.strategy_id,
                    instrument_id=order.instrument_id,
                    client_order_id=order.client_order_id,
                    reason=e.message,
                    ts_event=self._clock.timestamp_ns(),
                )

    async def _modify_order(self, command: ModifyOrder) -> None:
        """Modify an existing order."""
        venue_order_id = self._order_ids.get(command.client_order_id)

        if not venue_order_id:
            self._log.error(f"No venue order ID for {command.client_order_id}")
            return

        updates: dict[str, Any] = {"id": str(venue_order_id)}

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

            self._log.info(f"Order modified: {command.client_order_id}")

        except FyersApiError as e:
            self._log.error(f"Order modification failed: {e}")

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

            self._log.info(f"Order canceled: {command.client_order_id}")

        except FyersApiError as e:
            self._log.error(f"Order cancellation failed: {e}")

    async def _cancel_all_orders(self, command: CancelAllOrders) -> None:
        """Cancel all orders for an instrument."""
        # Get all open orders
        try:
            response = await self._http_client.get_orders()
            orders = response.get("orderBook", [])

            for order_data in orders:
                # Check if order is open and matches instrument
                status = order_data.get("status")
                if status in [3, 5, 7]:  # Transit, Pending, Partially Filled
                    symbol = order_data.get("symbol", "")
                    if command.instrument_id:
                        fyers_symbol = to_fyers_symbol(command.instrument_id)
                        if symbol != fyers_symbol:
                            continue

                    order_id = order_data.get("id")
                    await self._http_client.cancel_order(str(order_id))

            self._log.info(f"Canceled all orders for {command.instrument_id or 'all instruments'}")

        except FyersApiError as e:
            self._log.error(f"Cancel all orders failed: {e}")

    async def _batch_cancel_orders(self, command: BatchCancelOrders) -> None:
        """Batch cancel orders."""
        for cancel in command.cancels:
            await self._cancel_order(cancel)

    # -------------------------------------------------------------------------
    # Reports
    # -------------------------------------------------------------------------

    async def generate_order_status_report(
        self,
        command: GenerateOrderStatusReport,
    ) -> OrderStatusReport | None:
        """Generate order status report."""
        try:
            venue_order_id = command.venue_order_id
            if not venue_order_id:
                venue_order_id = self._order_ids.get(command.client_order_id)

            if not venue_order_id:
                return None

            response = await self._http_client.get_order(str(venue_order_id))
            order_data = response.get("orderBook", [{}])
            if isinstance(order_data, list) and len(order_data) > 0:
                order_data = order_data[0]

            return self._create_order_status_report(
                order_data,
                command.instrument_id,
                command.client_order_id,
                venue_order_id,
            )

        except FyersApiError as e:
            self._log.error(f"Failed to get order status: {e}")
            return None

    async def generate_order_status_reports(
        self,
        command: GenerateOrderStatusReports,
    ) -> list[OrderStatusReport]:
        """Generate order status reports for all orders."""
        reports = []

        try:
            response = await self._http_client.get_orders()

            for order_data in response.get("orderBook", []):
                venue_order_id = VenueOrderId(str(order_data.get("id", "")))
                client_order_id = self._venue_order_ids.get(venue_order_id)

                if not client_order_id:
                    continue

                instrument_id = self._cache.instrument(venue_order_id)
                if not instrument_id:
                    continue

                report = self._create_order_status_report(
                    order_data,
                    instrument_id,
                    client_order_id,
                    venue_order_id,
                )
                if report:
                    reports.append(report)

        except FyersApiError as e:
            self._log.error(f"Failed to get order reports: {e}")

        return reports

    async def generate_fill_reports(
        self,
        command: GenerateFillReports,
    ) -> list[FillReport]:
        """Generate fill reports."""
        reports = []

        try:
            response = await self._http_client.get_tradebook()

            for trade in response.get("tradeBook", []):
                report = self._create_fill_report(trade)
                if report:
                    reports.append(report)

        except FyersApiError as e:
            self._log.error(f"Failed to get fill reports: {e}")

        return reports

    async def generate_position_status_reports(
        self,
        command: GeneratePositionStatusReports,
    ) -> list[PositionStatusReport]:
        """Generate position status reports."""
        reports = []

        try:
            response = await self._http_client.get_positions()

            for pos_data in response.get("netPositions", []):
                report = self._create_position_report(pos_data)
                if report:
                    reports.append(report)

        except FyersApiError as e:
            self._log.error(f"Failed to get position reports: {e}")

        return reports

    async def generate_mass_status(
        self,
        lookback_mins: int | None = None,
    ):
        """Generate mass status (not supported)."""
        return None

    # -------------------------------------------------------------------------
    # Helper methods
    # -------------------------------------------------------------------------

    def _build_order_request(self, order: Order) -> dict[str, Any]:
        """Build a Fyers order request from a Nautilus order."""
        fyers_order = {
            "symbol": to_fyers_symbol(order.instrument_id),
            "qty": int(order.quantity),
            "type": to_fyers_order_type(order.order_type),
            "side": to_fyers_order_side(order.side),
            "productType": self._config.default_product_type.value,
            "validity": to_fyers_validity(order.time_in_force),
            "disclosedQty": 0,
            "offlineOrder": False,
        }

        # Add price for limit orders
        if order.price:
            fyers_order["limitPrice"] = float(order.price)

        # Add trigger price for stop orders
        if hasattr(order, "trigger_price") and order.trigger_price:
            fyers_order["stopPrice"] = float(order.trigger_price)

        return fyers_order

    def _create_order_status_report(
        self,
        data: dict[str, Any],
        instrument_id: InstrumentId,
        client_order_id: ClientOrderId,
        venue_order_id: VenueOrderId,
    ) -> OrderStatusReport | None:
        """Create an order status report from Fyers data."""
        try:
            return OrderStatusReport(
                account_id=self._account_id,
                instrument_id=instrument_id,
                client_order_id=client_order_id,
                venue_order_id=venue_order_id,
                order_side=OrderSide.BUY if data.get("side", 1) == 1 else OrderSide.SELL,
                order_type=OrderType.LIMIT if data.get("type", 1) == 1 else OrderType.MARKET,
                order_status=parse_order_status(data.get("status", 5)),
                quantity=Quantity.from_str(str(data.get("qty", 0))),
                filled_qty=Quantity.from_str(str(data.get("filledQty", data.get("tradedQty", 0)))),
                avg_px=Price.from_str(str(data.get("avgPrice", data.get("tradedPrice", 0)))),
                report_id=UUID4(),
                ts_accepted=self._clock.timestamp_ns(),
                ts_last=self._clock.timestamp_ns(),
                ts_init=self._clock.timestamp_ns(),
            )
        except Exception as e:
            self._log.error(f"Failed to create order report: {e}")
            return None

    def _create_fill_report(self, data: dict[str, Any]) -> FillReport | None:
        """Create a fill report from Fyers trade data."""
        try:
            from nautilus_trader.adapters.fyers.symbol import parse_fyers_symbol

            symbol = data.get("symbol", "")
            instrument_id = parse_fyers_symbol(symbol)

            return FillReport(
                account_id=self._account_id,
                instrument_id=instrument_id,
                venue_order_id=VenueOrderId(str(data.get("orderNumber", ""))),
                trade_id=TradeId(str(data.get("id", data.get("tradeNumber", "")))),
                order_side=OrderSide.BUY if data.get("side", 1) == 1 else OrderSide.SELL,
                last_qty=Quantity.from_str(str(data.get("tradedQty", data.get("qty", 0)))),
                last_px=Price.from_str(str(data.get("tradedPrice", data.get("tradePrice", 0)))),
                liquidity_side=LiquiditySide.NO_LIQUIDITY_SIDE,
                report_id=UUID4(),
                ts_event=self._clock.timestamp_ns(),
                ts_init=self._clock.timestamp_ns(),
            )
        except Exception as e:
            self._log.error(f"Failed to create fill report: {e}")
            return None

    def _create_position_report(self, data: dict[str, Any]) -> PositionStatusReport | None:
        """Create a position status report from Fyers position data."""
        try:
            parsed = parse_position(data)
            instrument_id = parsed["instrument_id"]
            net_qty = parsed["net_qty"]

            return PositionStatusReport(
                account_id=self._account_id,
                instrument_id=instrument_id,
                position_side=PositionSide.LONG if net_qty > 0 else PositionSide.SHORT,
                quantity=Quantity.from_str(str(abs(net_qty))),
                report_id=UUID4(),
                ts_last=self._clock.timestamp_ns(),
                ts_init=self._clock.timestamp_ns(),
            )
        except Exception as e:
            self._log.error(f"Failed to create position report: {e}")
            return None
