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
        buy_qty = self.settings.first_order_usdt / current_price
        self.state.total_qty += buy_qty
        self.state.total_usdt += self.settings.first_order_usdt
        self.state.avg_price = self.state.total_usdt / self.state.total_qty
        self.state.filled_safety = 0
        self.state.tp1_done = False
        self.state.tp2_done = False
        self.state.tp3_done = False
        self.state.tp_price = self.state.avg_price * (
            1 + self.settings.take_profit_pct / 100
        )
        self.logger.info("Открыта позиция по цене %.6f", current_price)
        self.logger.info("TP поставлен на %.6f", self.state.tp_price)
        self.logger.info(
            "Paper: позиция total_usdt=%.2f, total_qty=%.6f, avg=%.6f",
            self.state.total_usdt,
            self.state.total_qty,
            self.state.avg_price,
        )
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
        self.state.tp1_done = False
        self.state.tp2_done = False
        self.state.tp3_done = False

    def on_tick(self, current_price: float) -> None:
        if not self.state.running:
            return

        if self.state.position_open:
            self._check_safety(current_price)
            self._check_tp(current_price)

    def _check_safety(self, current_price: float) -> None:
        if self.state.filled_safety >= self.settings.safety_orders_count:
            return

        next_index = self.state.filled_safety + 1
        safety_price = self.state.entry_price * (
            1 - next_index * self.settings.safety_order_step_percent / 100
        )
        if current_price <= safety_price:
            qty = self.settings.safety_order_usdt / safety_price
            self.state.total_qty += qty
            self.state.total_usdt += self.settings.safety_order_usdt
        self.state.avg_price = self.state.total_usdt / self.state.total_qty
        self.state.filled_safety = next_index
        self.state.tp_price = self.state.avg_price * (
            1 + self.settings.take_profit_pct / 100
        )
        self.state.tp1_done = False
        self.state.tp2_done = False
        self.state.tp3_done = False
            self.logger.info(
                "Paper: safety order #%s filled at price=%.6f", next_index, safety_price
            )
            self.logger.info(
                "Исполнена страховка %s по цене %.6f", next_index, safety_price
            )
            self.logger.info(
                "Paper: позиция total_usdt=%.2f, total_qty=%.6f, avg=%.6f",
                self.state.total_usdt,
                self.state.total_qty,
                self.state.avg_price,
            )
            self.logger.info("Новая средняя цена %.6f", self.state.avg_price)
            self.logger.info("Новый TP %.6f", self.state.tp_price)
            self.emit_fn(
                "Исполнена страховка {} по {:.6f}, средняя {:.6f}, TP {:.6f}".format(
                    next_index, safety_price, self.state.avg_price, self.state.tp_price
                )
            )

    def _check_tp(self, current_price: float) -> None:
        if self.state.total_qty <= 0:
            return

        self._process_tp(
            current_price,
            "TP1",
            self.settings.tp1_percent,
            self.settings.tp1_share,
            "tp1_done",
        )
        self._process_tp(
            current_price,
            "TP2",
            self.settings.tp2_percent,
            self.settings.tp2_share,
            "tp2_done",
        )
        self._process_tp(
            current_price,
            "TP3",
            self.settings.tp3_percent,
            self.settings.tp3_share,
            "tp3_done",
        )

        if self.state.total_qty <= 0 or (
            self.state.tp1_done and self.state.tp2_done and self.state.tp3_done
        ):
            self.logger.info("Все TP выполнены, цикл закрыт")
            self.emit_fn("Все TP выполнены, цикл закрыт")
            self.state.cycles_closed += 1
            self._reset_position()

    def _process_tp(
        self,
        current_price: float,
        label: str,
        percent: float,
        share: int,
        done_attr: str,
    ) -> None:
        if getattr(self.state, done_attr):
            return
        if share == 0:
            setattr(self.state, done_attr, True)
            return
        target_price = self.state.avg_price * (1 + percent / 100)
        if current_price < target_price:
            return

        sell_qty = self.state.total_qty * (share / 100)
        if sell_qty <= 0:
            setattr(self.state, done_attr, True)
            return

        usdt_get = sell_qty * target_price
        cost_basis = sell_qty * self.state.avg_price
        pnl = usdt_get - cost_basis
        self.state.realized_pnl_usdt += pnl
        self.state.total_qty -= sell_qty
        self.state.total_usdt -= cost_basis
        setattr(self.state, done_attr, True)
        self.logger.info(
            "Paper: %s выполнен, цена=%.6f, qty=%.6f, pnl=%.2f",
            label,
            target_price,
            sell_qty,
            pnl,
        )
        self.emit_fn(f"Paper: {label} выполнен, прибыль {pnl:.2f} USDT")
