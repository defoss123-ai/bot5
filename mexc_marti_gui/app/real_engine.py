from __future__ import annotations

from dataclasses import dataclass, field

from .models import BotSettings


@dataclass
class RealState:
    running: bool = False
    position_open: bool = False
    entry_price: float = 0.0
    avg_price: float = 0.0
    total_qty: float = 0.0
    total_usdt: float = 0.0
    filled_safety: int = 0
    tp_price: float = 0.0
    realized_pnl_usdt: float = 0.0
    cycles_closed: int = 0
    entry_order_id: str = ""
    entry_status: str = ""
    tp_order_id: str = ""
    tp_status: str = ""
    safety_order_ids: list[str] = field(default_factory=list)
    last_status: str = ""


class RealEngine:
    def __init__(self, client, settings: BotSettings, logger, emit_fn) -> None:
        self.client = client
        self.settings = settings
        self.logger = logger
        self.emit_fn = emit_fn
        self.state = RealState()
        self._filled_order_ids: set[str] = set()
        self._tick_size: float | None = None
        self._step_size: float | None = None

    def start(self, clean_start: bool) -> None:
        self.state.running = True
        self.logger.info("Запуск реального режима")
        self.emit_fn("Запуск реального режима")
        self._load_exchange_info()
        self._check_balance()
        if clean_start:
            self.client.cancel_all_orders(self.settings.symbol)
            self.logger.info("Ордера отменены перед запуском")
            self.emit_fn("Ордера очищены перед запуском")

        current_price = self.client.get_price(self.settings.symbol)
        self._place_entry(current_price)
        self._place_safety_orders()

    def stop(self) -> None:
        self.state.running = False
        self.logger.info("Реальный режим остановлен")
        self.emit_fn("Реальный режим остановлен")

    def on_tick(self, auto_restart: bool) -> None:
        if not self.state.running:
            return

        self._update_orders(auto_restart)

    def cancel_all(self) -> None:
        self.client.cancel_all_orders(self.settings.symbol)
        self.logger.info("Ордера отменены вручную")
        self.emit_fn("Ордера отменены")

    def _load_exchange_info(self) -> None:
        tick_size, step_size = self.client.get_exchange_info(self.settings.symbol)
        self._tick_size = tick_size
        self._step_size = step_size

    def _check_balance(self) -> None:
        account = self.client.get_account()
        balances = account.get("balances", [])
        usdt_free = 0.0
        for item in balances:
            if item.get("asset") == "USDT":
                usdt_free = float(item.get("free", 0))
                break
        required = (1 + self.settings.safety_count) * self.settings.order_usdt
        if usdt_free < required:
            raise ValueError("Недостаточно USDT для запуска")

    def _place_entry(self, current_price: float) -> None:
        price = self._round_price(current_price)
        qty = self._round_qty(self.settings.order_usdt / price)
        if qty <= 0:
            raise ValueError("Недостаточный объём для входа")
        order = self.client.place_limit_buy(self.settings.symbol, price, qty)
        self.state.entry_order_id = str(order.get("orderId", ""))
        self.state.entry_status = order.get("status", "NEW")
        self.state.entry_price = price
        self.logger.info("Entry лимитка выставлена по цене %.6f", price)
        self.emit_fn(f"Входной ордер выставлен: {self.state.entry_order_id}")

    def _place_safety_orders(self) -> None:
        self.state.safety_order_ids = []
        for index in range(1, self.settings.safety_count + 1):
            price = self.state.entry_price * (
                1 - index * self.settings.safety_step_pct / 100
            )
            price = self._round_price(price)
            qty = self._round_qty(self.settings.order_usdt / price)
            if qty <= 0:
                continue
            order = self.client.place_limit_buy(self.settings.symbol, price, qty)
            order_id = str(order.get("orderId", ""))
            if order_id:
                self.state.safety_order_ids.append(order_id)
        if self.state.safety_order_ids:
            self.logger.info("Выставлены страховочные ордера: %s", self.state.safety_order_ids)
            self.emit_fn("Страховочные ордера выставлены")

    def _place_tp(self) -> None:
        if self.state.total_qty <= 0:
            return
        tp_price = self.state.avg_price * (1 + self.settings.take_profit_pct / 100)
        tp_price = self._round_price(tp_price)
        qty = self._round_qty(self.state.total_qty)
        if qty <= 0:
            raise ValueError("Недостаточный объём для TP")
        order = self.client.place_limit_sell(self.settings.symbol, tp_price, qty)
        self.state.tp_order_id = str(order.get("orderId", ""))
        self.state.tp_status = order.get("status", "NEW")
        self.state.tp_price = tp_price
        self.logger.info("TP лимитка выставлена по цене %.6f", tp_price)
        self.emit_fn(f"TP выставлен: {self.state.tp_order_id}")

    def _update_orders(self, auto_restart: bool) -> None:
        self._handle_entry_fill()
        self._handle_safety_fills()
        self._handle_tp_fill(auto_restart)

    def _handle_entry_fill(self) -> None:
        if not self.state.entry_order_id:
            return
        order = self.client.get_order(self.settings.symbol, self.state.entry_order_id)
        status = order.get("status", "")
        self.state.entry_status = status
        if status == "FILLED" and self.state.entry_order_id not in self._filled_order_ids:
            executed_qty = float(order.get("executedQty", 0))
            cummulative = float(order.get("cummulativeQuoteQty", 0))
            self._filled_order_ids.add(self.state.entry_order_id)
            self.state.total_qty += executed_qty
            self.state.total_usdt += cummulative
            self.state.avg_price = self.state.total_usdt / self.state.total_qty
            self.state.position_open = True
            self.logger.info("Entry исполнен, qty=%.6f, usdt=%.2f", executed_qty, cummulative)
            self.emit_fn("Вход исполнен")
            self._replace_tp()

    def _handle_safety_fills(self) -> None:
        for order_id in list(self.state.safety_order_ids):
            order = self.client.get_order(self.settings.symbol, order_id)
            status = order.get("status", "")
            if status == "FILLED" and order_id not in self._filled_order_ids:
                executed_qty = float(order.get("executedQty", 0))
                cummulative = float(order.get("cummulativeQuoteQty", 0))
                self._filled_order_ids.add(order_id)
                self.state.total_qty += executed_qty
                self.state.total_usdt += cummulative
                self.state.avg_price = self.state.total_usdt / self.state.total_qty
                self.state.filled_safety += 1
                self.logger.info(
                    "Страховка исполнена: qty=%.6f, usdt=%.2f", executed_qty, cummulative
                )
                self.emit_fn(f"Исполнена страховка {self.state.filled_safety}")
                self._replace_tp()

    def _handle_tp_fill(self, auto_restart: bool) -> None:
        if not self.state.tp_order_id:
            return
        order = self.client.get_order(self.settings.symbol, self.state.tp_order_id)
        status = order.get("status", "")
        self.state.tp_status = status
        if status == "FILLED":
            usdt_get = self.state.total_qty * self.state.tp_price
            pnl = usdt_get - self.state.total_usdt
            self.state.realized_pnl_usdt += pnl
            self.state.cycles_closed += 1
            self.logger.info("TP исполнен, прибыль %.2f USDT", pnl)
            self.emit_fn(f"TP исполнен, прибыль {pnl:.2f} USDT")
            self._reset_position()
            self._cancel_safety_orders()
            if auto_restart:
                current_price = self.client.get_price(self.settings.symbol)
                self._place_entry(current_price)
                self._place_safety_orders()

    def _cancel_safety_orders(self) -> None:
        for order_id in self.state.safety_order_ids:
            try:
                self.client.cancel_order(self.settings.symbol, order_id)
            except ValueError:
                continue
        self.state.safety_order_ids = []

    def _replace_tp(self) -> None:
        if self.state.tp_order_id:
            try:
                self.client.cancel_order(self.settings.symbol, self.state.tp_order_id)
            except ValueError:
                pass
        self._place_tp()

    def _reset_position(self) -> None:
        self.state.position_open = False
        self.state.entry_price = 0.0
        self.state.avg_price = 0.0
        self.state.total_qty = 0.0
        self.state.total_usdt = 0.0
        self.state.filled_safety = 0
        self.state.tp_price = 0.0
        self.state.entry_order_id = ""
        self.state.entry_status = ""
        self.state.tp_order_id = ""
        self.state.tp_status = ""
        self._filled_order_ids.clear()

    def _round_price(self, price: float) -> float:
        if self._tick_size is None:
            raise ValueError("Не задан tickSize")
        return self.client.round_price(price, self._tick_size)

    def _round_qty(self, qty: float) -> float:
        if self._step_size is None:
            raise ValueError("Не задан stepSize")
        return self.client.round_qty(qty, self._step_size)
