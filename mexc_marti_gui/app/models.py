from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BotSettings:
    symbol: str
    timeframe: str
    rsi_enabled: bool
    rsi_threshold: int
    order_usdt: float
    first_order_usdt: float
    safety_order_usdt: float
    safety_step_pct: float
    safety_count: int
    safety_orders_count: int
    safety_order_step_percent: float
    tp1_percent: float
    tp2_percent: float
    tp3_percent: float
    tp1_share: int
    tp2_share: int
    tp3_share: int
    take_profit_pct: float
    poll_seconds: int


@dataclass
class PaperState:
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
    tp1_done: bool = False
    tp2_done: bool = False
    tp3_done: bool = False
