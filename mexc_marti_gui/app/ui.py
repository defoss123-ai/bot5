import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from .logger import get_logger
from .indicators import calculate_rsi
from .mexc_api import MexcClient


def run_app() -> None:
    logger = get_logger()
    logger.info("UI started")

    root = tk.Tk()
    root.title("MEXC Спотовый Мартингейл-бот")

    ui_queue: queue.Queue[tuple[str, str | float]] = queue.Queue()
    simulation_event = threading.Event()
    simulation_thread: threading.Thread | None = None

    frame = tk.Frame(root)
    frame.pack(padx=20, pady=20)

    tk.Label(frame, text="API ключ").grid(row=0, column=0, sticky="w", pady=5)
    api_key_entry = tk.Entry(frame, width=50)
    api_key_entry.grid(row=0, column=1, pady=5)

    tk.Label(frame, text="API секрет").grid(row=1, column=0, sticky="w", pady=5)
    api_secret_entry = tk.Entry(frame, width=50, show="*")
    api_secret_entry.grid(row=1, column=1, pady=5)

    tk.Label(frame, text="Базовый URL").grid(row=2, column=0, sticky="w", pady=5)
    base_url_entry = tk.Entry(frame, width=50)
    base_url_entry.insert(0, "https://api.mexc.com")
    base_url_entry.grid(row=2, column=1, pady=5)

    def handle_check_connection() -> None:
        api_key = api_key_entry.get().strip()
        api_secret = api_secret_entry.get().strip()
        base_url = base_url_entry.get().strip()

        logger.info("Checking MEXC connection")
        client = MexcClient(api_key=api_key, api_secret=api_secret, base_url=base_url)
        success, message = client.check_connection()

        if success:
            logger.info("MEXC connection successful")
            messagebox.showinfo("Успех", "Подключение к MEXC успешно")
            enqueue_log("Подключение к MEXC успешно")
        else:
            logger.error("MEXC connection error: %s", message)
            messagebox.showerror("Ошибка", message)
            enqueue_log(f"Ошибка подключения к MEXC: {message}")

    check_button = tk.Button(
        frame, text="Проверить подключение", command=handle_check_connection
    )
    check_button.grid(row=3, column=0, columnspan=2, pady=10)

    strategy_frame = tk.LabelFrame(root, text="Настройки стратегии")
    strategy_frame.pack(padx=20, pady=10, fill="x")

    tk.Label(strategy_frame, text="Торговая пара").grid(
        row=0, column=0, sticky="w", padx=10, pady=5
    )
    pair_entry = tk.Entry(strategy_frame, width=30)
    pair_entry.insert(0, "BTCUSDT")
    pair_entry.grid(row=0, column=1, sticky="w", pady=5)

    tk.Label(strategy_frame, text="Таймфрейм").grid(
        row=1, column=0, sticky="w", padx=10, pady=5
    )
    timeframe_combo = ttk.Combobox(
        strategy_frame, values=["1m", "5m", "15m", "1h"], state="readonly", width=27
    )
    timeframe_combo.set("1m")
    timeframe_combo.grid(row=1, column=1, sticky="w", pady=5)

    tk.Label(strategy_frame, text="RSI меньше чем").grid(
        row=2, column=0, sticky="w", padx=10, pady=5
    )
    rsi_entry = tk.Entry(strategy_frame, width=30)
    rsi_entry.insert(0, "30")
    rsi_entry.grid(row=2, column=1, sticky="w", pady=5)

    price_value = tk.StringVar(value="—")
    rsi_value = tk.StringVar(value="—")

    market_info_frame = tk.Frame(strategy_frame)
    market_info_frame.grid(row=3, column=0, columnspan=2, sticky="w", padx=10, pady=5)
    tk.Label(market_info_frame, text="Цена:").pack(side=tk.LEFT)
    tk.Label(market_info_frame, textvariable=price_value).pack(side=tk.LEFT, padx=5)
    tk.Label(market_info_frame, text="RSI:").pack(side=tk.LEFT, padx=15)
    tk.Label(market_info_frame, textvariable=rsi_value).pack(side=tk.LEFT, padx=5)

    market_buttons_frame = tk.Frame(strategy_frame)
    market_buttons_frame.grid(row=4, column=0, columnspan=2, sticky="w", padx=10, pady=5)
    get_price_button = tk.Button(
        market_buttons_frame, text="Получить цену", command=handle_get_price
    )
    get_price_button.pack(side=tk.LEFT, padx=5)
    check_rsi_button = tk.Button(
        market_buttons_frame, text="Проверить RSI", command=handle_check_rsi
    )
    check_rsi_button.pack(side=tk.LEFT, padx=5)

    paper_mode_var = tk.BooleanVar(value=True)
    paper_mode_check = tk.Checkbutton(
        strategy_frame, text="Paper mode (без реальных ордеров)", variable=paper_mode_var
    )
    paper_mode_check.grid(row=5, column=0, columnspan=2, sticky="w", padx=10, pady=5)

    tk.Label(strategy_frame, text="Take Profit %").grid(
        row=6, column=0, sticky="w", padx=10, pady=5
    )
    tp_entry = tk.Entry(strategy_frame, width=30)
    tp_entry.insert(0, "1.0")
    tp_entry.grid(row=6, column=1, sticky="w", pady=5)

    tk.Label(strategy_frame, text="Шаг страховочного ордера %").grid(
        row=7, column=0, sticky="w", padx=10, pady=5
    )
    safety_step_entry = tk.Entry(strategy_frame, width=30)
    safety_step_entry.insert(0, "2.0")
    safety_step_entry.grid(row=7, column=1, sticky="w", pady=5)

    tk.Label(strategy_frame, text="Кол-во страховочных ордеров").grid(
        row=8, column=0, sticky="w", padx=10, pady=5
    )
    safety_count_entry = tk.Entry(strategy_frame, width=30)
    safety_count_entry.insert(0, "5")
    safety_count_entry.grid(row=8, column=1, sticky="w", pady=5)

    def update_status(text: str) -> None:
        status_text.configure(state="normal")
        status_text.delete("1.0", tk.END)
        status_text.insert(tk.END, text)
        status_text.configure(state="disabled")

    def append_log(message: str) -> None:
        log_text.configure(state="normal")
        log_text.insert(tk.END, f"{message}\n")
        log_text.see(tk.END)
        log_text.configure(state="disabled")

    def enqueue_log(message: str) -> None:
        ui_queue.put(("log", message))

    def enqueue_error(message: str) -> None:
        ui_queue.put(("error", message))

    def process_ui_queue() -> None:
        while True:
            try:
                item_type, payload = ui_queue.get_nowait()
            except queue.Empty:
                break

            if item_type == "log":
                append_log(str(payload))
            elif item_type == "price":
                price_value.set(f"{payload:.6f}")
            elif item_type == "rsi":
                rsi_value.set(f"{payload:.2f}")
            elif item_type == "error":
                messagebox.showerror("Ошибка", str(payload))
        root.after(200, process_ui_queue)

    def handle_start() -> None:
        pair = pair_entry.get().strip()
        if not pair:
            logger.error("Ошибка валидации: торговая пара пуста")
            messagebox.showerror("Ошибка", "Торговая пара не должна быть пустой")
            return

        try:
            rsi_value = int(rsi_entry.get().strip())
        except ValueError:
            logger.error("Ошибка валидации: RSI не целое число")
            messagebox.showerror("Ошибка", "RSI должен быть целым числом")
            return

        if not 1 <= rsi_value <= 99:
            logger.error("Ошибка валидации: RSI вне диапазона 1..99")
            messagebox.showerror("Ошибка", "RSI должен быть в диапазоне 1..99")
            return

        try:
            tp_value = float(tp_entry.get().strip())
        except ValueError:
            logger.error("Ошибка валидации: Take Profit не число")
            messagebox.showerror("Ошибка", "Take Profit должен быть числом")
            return

        if tp_value <= 0:
            logger.error("Ошибка валидации: Take Profit меньше или равен 0")
            messagebox.showerror("Ошибка", "Take Profit должен быть больше 0")
            return

        try:
            safety_step_value = float(safety_step_entry.get().strip())
        except ValueError:
            logger.error("Ошибка валидации: шаг страховочного ордера не число")
            messagebox.showerror(
                "Ошибка", "Шаг страховочного ордера должен быть числом"
            )
            return

        if safety_step_value <= 0:
            logger.error("Ошибка валидации: шаг страховочного ордера <= 0")
            messagebox.showerror(
                "Ошибка", "Шаг страховочного ордера должен быть больше 0"
            )
            return

        try:
            safety_count_value = int(safety_count_entry.get().strip())
        except ValueError:
            logger.error("Ошибка валидации: кол-во страховочных ордеров не целое число")
            messagebox.showerror(
                "Ошибка", "Кол-во страховочных ордеров должно быть целым числом"
            )
            return

        if safety_count_value < 0:
            logger.error("Ошибка валидации: кол-во страховочных ордеров < 0")
            messagebox.showerror(
                "Ошибка", "Кол-во страховочных ордеров должно быть 0 или больше"
            )
            return

        timeframe_value = timeframe_combo.get()
        logger.info(
            "Старт стратегии: пара=%s, таймфрейм=%s, RSI<%s, TP=%s%%, шаг страховки=%s%%, страховок=%s",
            pair,
            timeframe_value,
            rsi_value,
            tp_value,
            safety_step_value,
            safety_count_value,
        )
        start_button.configure(state="disabled")
        update_status("Бот запущен (пока без торговли)")
        enqueue_log("Бот запущен (пока без торговли)")

    def handle_stop() -> None:
        logger.info("Бот остановлен")
        start_button.configure(state="normal")
        update_status("Бот остановлен")
        enqueue_log("Бот остановлен")

    def get_client() -> MexcClient:
        return MexcClient(
            api_key=api_key_entry.get().strip(),
            api_secret=api_secret_entry.get().strip(),
            base_url=base_url_entry.get().strip(),
        )

    def get_rsi_threshold() -> int | None:
        try:
            return int(rsi_entry.get().strip())
        except ValueError:
            logger.error("Ошибка ввода: RSI порог должен быть целым числом")
            enqueue_error("RSI должен быть целым числом")
            return None

    def extract_closes(klines: list) -> list[float]:
        closes: list[float] = []
        for item in klines:
            if isinstance(item, list) and len(item) > 4:
                closes.append(float(item[4]))
            elif isinstance(item, dict) and "close" in item:
                closes.append(float(item["close"]))
        return closes

    def handle_get_price() -> None:
        symbol = pair_entry.get().strip()
        if not symbol:
            logger.error("Ошибка ввода: торговая пара пуста для получения цены")
            messagebox.showerror("Ошибка", "Торговая пара не должна быть пустой")
            return

        def worker() -> None:
            try:
                price = get_client().get_price(symbol)
            except Exception as exc:  # noqa: BLE001
                logger.error("Ошибка получения цены: %s", exc)
                enqueue_error(str(exc))
                enqueue_log(f"Ошибка получения цены: {exc}")
                return
            logger.info("Цена %s: %.6f", symbol, price)
            enqueue_log(f"Цена {symbol}: {price:.6f}")
            ui_queue.put(("price", price))

        threading.Thread(target=worker, daemon=True).start()

    def handle_check_rsi() -> None:
        symbol = pair_entry.get().strip()
        if not symbol:
            logger.error("Ошибка ввода: торговая пара пуста для RSI")
            messagebox.showerror("Ошибка", "Торговая пара не должна быть пустой")
            return

        threshold = get_rsi_threshold()
        if threshold is None:
            return

        interval = timeframe_combo.get()

        def worker() -> None:
            try:
                klines = get_client().get_klines(symbol, interval, limit=200)
                closes = extract_closes(klines)
                rsi = calculate_rsi(closes)
            except Exception as exc:  # noqa: BLE001
                logger.error("Ошибка расчёта RSI: %s", exc)
                enqueue_error(str(exc))
                enqueue_log(f"Ошибка расчёта RSI: {exc}")
                return

            logger.info("RSI %s (%s): %.2f", symbol, interval, rsi)
            enqueue_log(f"RSI {symbol} ({interval}): {rsi:.2f}")
            ui_queue.put(("rsi", rsi))
            if rsi < threshold:
                logger.info("RSI фильтр пройден")
                enqueue_log("RSI фильтр пройден")
            else:
                logger.info("RSI фильтр не пройден")
                enqueue_log("RSI фильтр не пройден")

        threading.Thread(target=worker, daemon=True).start()

    def run_simulation() -> None:
        symbol = pair_entry.get().strip()
        interval = timeframe_combo.get()
        threshold = get_rsi_threshold()
        if not symbol:
            logger.error("Ошибка ввода: торговая пара пуста для симуляции")
            enqueue_error("Торговая пара не должна быть пустой")
            return
        if threshold is None:
            return

        logger.info("Запуск симуляции для %s (%s)", symbol, interval)
        enqueue_log(f"Симуляция запущена для {symbol} ({interval})")

        while not simulation_event.is_set():
            try:
                client = get_client()
                price = client.get_price(symbol)
                klines = client.get_klines(symbol, interval, limit=200)
                closes = extract_closes(klines)
                rsi = calculate_rsi(closes)
            except Exception as exc:  # noqa: BLE001
                logger.error("Ошибка симуляции: %s", exc)
                enqueue_log(f"Ошибка симуляции: {exc}")
                if simulation_event.wait(10):
                    break
                continue

            ui_queue.put(("price", price))
            ui_queue.put(("rsi", rsi))
            enqueue_log(f"Цена {symbol}: {price:.6f}, RSI: {rsi:.2f}")

            if rsi < threshold:
                logger.info("Можно входить")
                enqueue_log("Можно входить")
            else:
                logger.info("Ждём")
                enqueue_log("Ждём")

            if simulation_event.wait(10):
                break

        logger.info("Симуляция остановлена")
        enqueue_log("Симуляция остановлена")

    def handle_sim_start() -> None:
        nonlocal simulation_thread
        if simulation_thread and simulation_thread.is_alive():
            return
        simulation_event.clear()
        simulation_thread = threading.Thread(target=run_simulation, daemon=True)
        simulation_thread.start()
        sim_start_button.configure(state="disabled")
        logger.info("Старт симуляции")
        enqueue_log("Старт симуляции")

    def handle_sim_stop() -> None:
        simulation_event.set()
        sim_start_button.configure(state="normal")
        logger.info("Остановлено")
        enqueue_log("Остановлено")

    buttons_frame = tk.Frame(strategy_frame)
    buttons_frame.grid(row=9, column=0, columnspan=2, pady=10)

    start_button = tk.Button(
        buttons_frame, text="▶ Старт стратегии", command=handle_start
    )
    start_button.pack(side=tk.LEFT, padx=5)

    stop_button = tk.Button(
        buttons_frame, text="⏹ Стоп стратегии", command=handle_stop
    )
    stop_button.pack(side=tk.LEFT, padx=5)

    sim_buttons_frame = tk.Frame(strategy_frame)
    sim_buttons_frame.grid(row=10, column=0, columnspan=2, pady=5)
    sim_start_button = tk.Button(
        sim_buttons_frame, text="Старт (симуляция)", command=handle_sim_start
    )
    sim_start_button.pack(side=tk.LEFT, padx=5)
    sim_stop_button = tk.Button(
        sim_buttons_frame, text="Стоп", command=handle_sim_stop
    )
    sim_stop_button.pack(side=tk.LEFT, padx=5)

    status_text = tk.Text(root, height=2, width=60, state="disabled")
    status_text.pack(padx=20, pady=10, fill="x")

    log_text = tk.Text(root, height=8, width=60, state="disabled")
    log_text.pack(padx=20, pady=10, fill="both")

    orders_frame = tk.LabelFrame(root, text="Настройки ордеров")
    orders_frame.pack(padx=20, pady=10, fill="x")

    tk.Label(orders_frame, text="Стартовая цена").grid(
        row=0, column=0, sticky="w", padx=10, pady=5
    )
    start_price_entry = tk.Entry(orders_frame, width=30)
    start_price_entry.insert(0, "1.0000")
    start_price_entry.grid(row=0, column=1, sticky="w", pady=5)

    tk.Label(orders_frame, text="Сумма на 1 ордер (USDT)").grid(
        row=1, column=0, sticky="w", padx=10, pady=5
    )
    sum_usdt_entry = tk.Entry(orders_frame, width=30)
    sum_usdt_entry.insert(0, "10")
    sum_usdt_entry.grid(row=1, column=1, sticky="w", pady=5)

    tk.Label(orders_frame, text="Шаг страховочного ордера (%)").grid(
        row=2, column=0, sticky="w", padx=10, pady=5
    )
    order_step_entry = tk.Entry(orders_frame, width=30)
    order_step_entry.insert(0, "2")
    order_step_entry.grid(row=2, column=1, sticky="w", pady=5)

    tk.Label(orders_frame, text="Кол-во страховочных ордеров").grid(
        row=3, column=0, sticky="w", padx=10, pady=5
    )
    order_count_entry = tk.Entry(orders_frame, width=30)
    order_count_entry.insert(0, "5")
    order_count_entry.grid(row=3, column=1, sticky="w", pady=5)

    orders_table = ttk.Treeview(
        root,
        columns=("index", "price", "sum", "amount"),
        show="headings",
        height=6,
    )
    orders_table.heading("index", text="№")
    orders_table.heading("price", text="Цена")
    orders_table.heading("sum", text="Сумма USDT")
    orders_table.heading("amount", text="Кол-во монет")
    orders_table.column("index", width=40, anchor="center")
    orders_table.column("price", width=120, anchor="center")
    orders_table.column("sum", width=120, anchor="center")
    orders_table.column("amount", width=140, anchor="center")

    tp_frame = tk.LabelFrame(root, text="Тейк-профиты (TP)")
    tp_frame.pack(padx=20, pady=10, fill="x")

    tk.Label(tp_frame, text="TP1 (%)").grid(row=0, column=0, sticky="w", padx=10, pady=5)
    tp1_entry = tk.Entry(tp_frame, width=12)
    tp1_entry.insert(0, "1.0")
    tp1_entry.grid(row=0, column=1, sticky="w", pady=5)

    tk.Label(tp_frame, text="Доля TP1 (%)").grid(
        row=0, column=2, sticky="w", padx=10, pady=5
    )
    tp1_share_entry = tk.Entry(tp_frame, width=12)
    tp1_share_entry.insert(0, "30")
    tp1_share_entry.grid(row=0, column=3, sticky="w", pady=5)

    tk.Label(tp_frame, text="TP2 (%)").grid(row=1, column=0, sticky="w", padx=10, pady=5)
    tp2_entry = tk.Entry(tp_frame, width=12)
    tp2_entry.insert(0, "2.0")
    tp2_entry.grid(row=1, column=1, sticky="w", pady=5)

    tk.Label(tp_frame, text="Доля TP2 (%)").grid(
        row=1, column=2, sticky="w", padx=10, pady=5
    )
    tp2_share_entry = tk.Entry(tp_frame, width=12)
    tp2_share_entry.insert(0, "30")
    tp2_share_entry.grid(row=1, column=3, sticky="w", pady=5)

    tk.Label(tp_frame, text="TP3 (%)").grid(row=2, column=0, sticky="w", padx=10, pady=5)
    tp3_entry = tk.Entry(tp_frame, width=12)
    tp3_entry.insert(0, "3.0")
    tp3_entry.grid(row=2, column=1, sticky="w", pady=5)

    tk.Label(tp_frame, text="Доля TP3 (%)").grid(
        row=2, column=2, sticky="w", padx=10, pady=5
    )
    tp3_share_entry = tk.Entry(tp_frame, width=12)
    tp3_share_entry.insert(0, "40")
    tp3_share_entry.grid(row=2, column=3, sticky="w", pady=5)

    tk.Label(tp_frame, text="Сумма долей должна быть 100%").grid(
        row=3, column=0, columnspan=4, sticky="w", padx=10, pady=5
    )

    totals_frame = tk.LabelFrame(root, text="Итоги")
    totals_frame.pack(padx=20, pady=10, fill="x")

    total_usdt_value = tk.StringVar(value="0.00")
    total_qty_value = tk.StringVar(value="0.000000")
    avg_price_value = tk.StringVar(value="0.000000")

    tk.Label(totals_frame, text="Всего USDT").grid(
        row=0, column=0, sticky="w", padx=10, pady=5
    )
    tk.Label(totals_frame, textvariable=total_usdt_value).grid(
        row=0, column=1, sticky="w", padx=10, pady=5
    )
    tk.Label(totals_frame, text="Всего монет").grid(
        row=0, column=2, sticky="w", padx=10, pady=5
    )
    tk.Label(totals_frame, textvariable=total_qty_value).grid(
        row=0, column=3, sticky="w", padx=10, pady=5
    )
    tk.Label(totals_frame, text="Средняя цена").grid(
        row=0, column=4, sticky="w", padx=10, pady=5
    )
    tk.Label(totals_frame, textvariable=avg_price_value).grid(
        row=0, column=5, sticky="w", padx=10, pady=5
    )

    tp_table_frame = tk.LabelFrame(root, text="План TP")
    tp_table_frame.pack(padx=20, pady=10, fill="x")

    tp_table = ttk.Treeview(
        tp_table_frame,
        columns=("level", "sell_price", "sell_qty", "usdt_get", "profit"),
        show="headings",
        height=5,
    )
    tp_table.heading("level", text="Уровень")
    tp_table.heading("sell_price", text="Цена продажи")
    tp_table.heading("sell_qty", text="Монет продать")
    tp_table.heading("usdt_get", text="USDT получить")
    tp_table.heading("profit", text="Прибыль (USDT)")
    tp_table.column("level", width=80, anchor="center")
    tp_table.column("sell_price", width=140, anchor="center")
    tp_table.column("sell_qty", width=140, anchor="center")
    tp_table.column("usdt_get", width=140, anchor="center")
    tp_table.column("profit", width=140, anchor="center")

    def clear_orders_table() -> None:
        for item in orders_table.get_children():
            orders_table.delete(item)

    def clear_tp_table() -> None:
        for item in tp_table.get_children():
            tp_table.delete(item)

    def handle_calculate_orders() -> None:
        try:
            start_price = float(start_price_entry.get().strip())
            sum_usdt = float(sum_usdt_entry.get().strip())
            step_pct = float(order_step_entry.get().strip())
            order_count = int(order_count_entry.get().strip())
            tp1_pct = float(tp1_entry.get().strip())
            tp1_share = float(tp1_share_entry.get().strip())
            tp2_pct = float(tp2_entry.get().strip())
            tp2_share = float(tp2_share_entry.get().strip())
            tp3_pct = float(tp3_entry.get().strip())
            tp3_share = float(tp3_share_entry.get().strip())
        except ValueError:
            logger.error("Ошибка ввода при расчёте страховочных ордеров")
            messagebox.showerror("Ошибка", "Введите корректные числа")
            return

        if (
            start_price <= 0
            or sum_usdt <= 0
            or step_pct <= 0
            or order_count < 0
            or tp1_pct <= 0
            or tp1_share <= 0
            or tp2_pct <= 0
            or tp2_share <= 0
            or tp3_pct <= 0
            or tp3_share <= 0
        ):
            logger.error("Некорректные значения для расчёта страховочных ордеров")
            messagebox.showerror("Ошибка", "Введите корректные числа")
            return

        shares_sum = tp1_share + tp2_share + tp3_share
        if abs(shares_sum - 100.0) > 0.01:
            logger.error("Сумма долей TP не равна 100%%: %s", shares_sum)
            messagebox.showerror("Ошибка", "Сумма долей TP должна быть 100%")
            return

        clear_orders_table()
        clear_tp_table()

        total_usdt = sum_usdt * (1 + order_count)
        total_qty = 0.0

        order0_qty = sum_usdt / start_price
        total_qty += order0_qty
        orders_table.insert(
            "",
            "end",
            values=(0, f"{start_price:.6f}", f"{sum_usdt:.2f}", f"{order0_qty:.6f}"),
        )

        for index in range(1, order_count + 1):
            price = start_price * (1 - (index * step_pct / 100))
            if price <= 0:
                continue
            amount = sum_usdt / price
            total_qty += amount
            orders_table.insert(
                "",
                "end",
                values=(
                    index,
                    f"{price:.6f}",
                    f"{sum_usdt:.2f}",
                    f"{amount:.6f}",
                ),
            )

        avg_price = total_usdt / total_qty if total_qty > 0 else 0.0
        total_usdt_value.set(f"{total_usdt:.2f}")
        total_qty_value.set(f"{total_qty:.6f}")
        avg_price_value.set(f"{avg_price:.6f}")

        tp_levels = [
            ("TP1", tp1_pct, tp1_share),
            ("TP2", tp2_pct, tp2_share),
            ("TP3", tp3_pct, tp3_share),
        ]
        for level, tp_pct, share_pct in tp_levels:
            sell_price = avg_price * (1 + tp_pct / 100)
            sell_qty = total_qty * (share_pct / 100)
            usdt_get = sell_qty * sell_price
            cost_basis = sell_qty * avg_price
            profit = usdt_get - cost_basis
            tp_table.insert(
                "",
                "end",
                values=(
                    level,
                    f"{sell_price:.6f}",
                    f"{sell_qty:.6f}",
                    f"{usdt_get:.2f}",
                    f"{profit:.2f}",
                ),
            )

        logger.info(
            "Calculated safety orders: %s, step=%s, start=%s, sum=%s",
            order_count,
            step_pct,
            start_price,
            sum_usdt,
        )
        logger.info(
            "Totals: avg_price=%s, total_usdt=%s, total_qty=%s, tp=[%s/%s/%s], shares=[%s/%s/%s]",
            avg_price,
            total_usdt,
            total_qty,
            tp1_pct,
            tp2_pct,
            tp3_pct,
            tp1_share,
            tp2_share,
            tp3_share,
        )
        enqueue_log(
            "Итоги расчёта: средняя цена={:.6f}, всего USDT={:.2f}, всего монет={:.6f}".format(
                avg_price, total_usdt, total_qty
            )
        )

    calculate_button = tk.Button(
        orders_frame, text="Рассчитать", command=handle_calculate_orders
    )
    calculate_button.grid(row=4, column=0, columnspan=2, pady=10)

    orders_table.pack(padx=20, pady=10, fill="x")
    tp_table.pack(padx=10, pady=10, fill="x")

    exit_button = tk.Button(root, text="Выход", command=root.destroy)
    exit_button.pack(pady=10)

    root.after(200, process_ui_queue)
    root.mainloop()
