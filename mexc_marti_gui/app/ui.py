import tkinter as tk
from tkinter import messagebox, ttk

from .logger import get_logger
from .mexc_api import MexcClient


def run_app() -> None:
    logger = get_logger()
    logger.info("UI started")

    root = tk.Tk()
    root.title("MEXC Спотовый Мартингейл-бот")

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
        else:
            logger.error("MEXC connection error: %s", message)
            messagebox.showerror("Ошибка", message)

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

    tk.Label(strategy_frame, text="Take Profit %").grid(
        row=3, column=0, sticky="w", padx=10, pady=5
    )
    tp_entry = tk.Entry(strategy_frame, width=30)
    tp_entry.insert(0, "1.0")
    tp_entry.grid(row=3, column=1, sticky="w", pady=5)

    tk.Label(strategy_frame, text="Шаг страховочного ордера %").grid(
        row=4, column=0, sticky="w", padx=10, pady=5
    )
    safety_step_entry = tk.Entry(strategy_frame, width=30)
    safety_step_entry.insert(0, "2.0")
    safety_step_entry.grid(row=4, column=1, sticky="w", pady=5)

    tk.Label(strategy_frame, text="Кол-во страховочных ордеров").grid(
        row=5, column=0, sticky="w", padx=10, pady=5
    )
    safety_count_entry = tk.Entry(strategy_frame, width=30)
    safety_count_entry.insert(0, "5")
    safety_count_entry.grid(row=5, column=1, sticky="w", pady=5)

    def update_status(text: str) -> None:
        status_text.configure(state="normal")
        status_text.delete("1.0", tk.END)
        status_text.insert(tk.END, text)
        status_text.configure(state="disabled")

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

    def handle_stop() -> None:
        logger.info("Бот остановлен")
        start_button.configure(state="normal")
        update_status("Бот остановлен")

    buttons_frame = tk.Frame(strategy_frame)
    buttons_frame.grid(row=6, column=0, columnspan=2, pady=10)

    start_button = tk.Button(buttons_frame, text="▶ Старт", command=handle_start)
    start_button.pack(side=tk.LEFT, padx=5)

    stop_button = tk.Button(buttons_frame, text="⏹ Стоп", command=handle_stop)
    stop_button.pack(side=tk.LEFT, padx=5)

    status_text = tk.Text(root, height=2, width=60, state="disabled")
    status_text.pack(padx=20, pady=10, fill="x")

    exit_button = tk.Button(root, text="Выход", command=root.destroy)
    exit_button.pack(pady=10)

    root.mainloop()
