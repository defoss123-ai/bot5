from __future__ import annotations

from .models import BotSettings, PaperState


class PaperEngine:
    def __init__(self, client, settings: BotSettings, logger, emit_fn) -> None:
        self.client = client
        self.settings = settings
        self.logger = logger
        self.emit_fn = emit_fn
        self.state = PaperState()

    def start(self) -> None:
        self.state.running = True
        self.logger.info("PaperEngine запущен")
        self.emit_fn("PaperEngine запущен")

    def stop(self) -> None:
        self.state.running = False
        self.logger.info("PaperEngine остановлен")
        self.emit_fn("PaperEngine остановлен")

    def open_position(self, current_price: float) -> None:
        self.state.position_open = True
        self.state.entry_price = current_price
        buy_qty = self.settings.order_usdt / current_price
        self.state.total_qty += buy_qty
        self.state.total_usdt += self.settings.order_usdt
        self.state.avg_price = self.state.total_usdt / self.state.total_qty
        self.state.filled_safety = 0
        self.state.tp_price = self.state.avg_price * (
            1 + self.settings.take_profit_pct / 100
        )
        self.logger.info("Открыта позиция по цене %.6f", current_price)
        self.logger.info("TP поставлен на %.6f", self.state.tp_price)
        self.emit_fn(
            f"Открыта позиция по цене {current_price:.6f}, TP {self.state.tp_price:.6f}"
        )

    def _reset_position(self) -> None:
        self.state.position_open = False
        self.state.entry_price = 0.0
        self.state.avg_price = 0.0
        self.state.total_qty = 0.0
        self.state.total_usdt = 0.0
        self.state.filled_safety = 0
        self.state.tp_price = 0.0

    def on_tick(self, current_price: float) -> None:
        if not self.state.running:
            return

        if self.state.position_open:
            self._check_safety(current_price)
            self._check_tp(current_price)

    def _check_safety(self, current_price: float) -> None:
        if self.state.filled_safety >= self.settings.safety_count:
            return

        next_index = self.state.filled_safety + 1
        safety_price = self.state.entry_price * (
            1 - next_index * self.settings.safety_step_pct / 100
        )
        if current_price <= safety_price:
            qty = self.settings.order_usdt / safety_price
            self.state.total_qty += qty
            self.state.total_usdt += self.settings.order_usdt
            self.state.avg_price = self.state.total_usdt / self.state.total_qty
            self.state.filled_safety = next_index
            self.state.tp_price = self.state.avg_price * (
                1 + self.settings.take_profit_pct / 100
            )
            self.logger.info(
                "Исполнена страховка %s по цене %.6f", next_index, safety_price
            )
            self.logger.info("Новая средняя цена %.6f", self.state.avg_price)
            self.logger.info("Новый TP %.6f", self.state.tp_price)
            self.emit_fn(
                "Исполнена страховка {} по {:.6f}, средняя {:.6f}, TP {:.6f}".format(
                    next_index, safety_price, self.state.avg_price, self.state.tp_price
                )
            )

    def _check_tp(self, current_price: float) -> None:
        if self.state.tp_price <= 0:
            return
        if current_price >= self.state.tp_price:
            usdt_get = self.state.total_qty * self.state.tp_price
            pnl = usdt_get - self.state.total_usdt
            self.state.realized_pnl_usdt += pnl
            self.state.cycles_closed += 1
            self.logger.info("TP исполнен, прибыль %.2f USDT", pnl)
            self.logger.info("Цикл закрыт")
            self.emit_fn(f"TP исполнен, прибыль {pnl:.2f} USDT, цикл закрыт")
            self._reset_position()
