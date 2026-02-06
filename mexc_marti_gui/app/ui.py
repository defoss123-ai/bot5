import threading
import tkinter as tk
from tkinter import ttk

from .logger import get_logger
from .mexc_client import MexcClient


DEFAULT_BASE_URL = "https://api.mexc.com"


def run_app(api_key: str = "", api_secret: str = "", base_url: str = DEFAULT_BASE_URL) -> None:
    logger = get_logger()
    logger.info("UI started")

    root = tk.Tk()
    root.title("MEXC Спотовый Мартингейл-бот")

    api_key_var = tk.StringVar(value=api_key)
    api_secret_var = tk.StringVar(value=api_secret)
    base_url_var = tk.StringVar(value=base_url or DEFAULT_BASE_URL)

    main_frame = ttk.Frame(root, padding=12)
    main_frame.pack(fill=tk.BOTH, expand=True)

    ttk.Label(main_frame, text="Шаг 0: каркас готов").pack(anchor=tk.W, pady=(0, 10))

    form_frame = ttk.Frame(main_frame)
    form_frame.pack(fill=tk.X, pady=(0, 10))

    ttk.Label(form_frame, text="API Key:").grid(row=0, column=0, sticky=tk.W, pady=4)
    api_key_entry = ttk.Entry(form_frame, textvariable=api_key_var, width=50)
    api_key_entry.grid(row=0, column=1, sticky=tk.EW, pady=4)

    ttk.Label(form_frame, text="API Secret:").grid(row=1, column=0, sticky=tk.W, pady=4)
    api_secret_entry = ttk.Entry(form_frame, textvariable=api_secret_var, show="*", width=50)
    api_secret_entry.grid(row=1, column=1, sticky=tk.EW, pady=4)

    ttk.Label(form_frame, text="Base URL:").grid(row=2, column=0, sticky=tk.W, pady=4)
    base_url_entry = ttk.Entry(form_frame, textvariable=base_url_var, width=50)
    base_url_entry.grid(row=2, column=1, sticky=tk.EW, pady=4)

    form_frame.columnconfigure(1, weight=1)

    status_text = tk.Text(main_frame, height=8, wrap=tk.WORD)
    status_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
    status_text.configure(state=tk.DISABLED)

    button_frame = ttk.Frame(main_frame)
    button_frame.pack(fill=tk.X)

    check_button = ttk.Button(button_frame, text="Проверить подключение")
    check_button.pack(side=tk.LEFT)

    exit_button = ttk.Button(button_frame, text="Выход", command=root.destroy)
    exit_button.pack(side=tk.RIGHT)

    def append_status(message: str) -> None:
        status_text.configure(state=tk.NORMAL)
        status_text.insert(tk.END, message + "\n")
        status_text.see(tk.END)
        status_text.configure(state=tk.DISABLED)

    def set_status(message: str) -> None:
        root.after(0, lambda: append_status(message))

    def run_check() -> None:
        api_key_value = api_key_var.get().strip()
        api_secret_value = api_secret_var.get().strip()
        base_url_value = base_url_var.get().strip() or DEFAULT_BASE_URL

        if not api_key_value or not api_secret_value:
            set_status("Ошибка: введите API Key и API Secret.")
            logger.error("API ключи не заполнены")
            root.after(0, lambda: check_button.configure(state=tk.NORMAL))
            return

        client = MexcClient(api_key_value, api_secret_value, base_url_value)

        set_status("Проверка сети: запрос времени сервера...")
        time_response = client.get_server_time()
        if "_error" in time_response:
            set_status(time_response["_error"])
            root.after(0, lambda: check_button.configure(state=tk.NORMAL))
            return

        set_status("Проверка ключей: запрос аккаунта...")
        account_response = client.get_account()
        if "_error" in account_response:
            set_status(account_response["_error"])
            root.after(0, lambda: check_button.configure(state=tk.NORMAL))
            return

        set_status("Успех: подключение к MEXC подтверждено.")
        root.after(0, lambda: check_button.configure(state=tk.NORMAL))

    def on_check() -> None:
        check_button.configure(state=tk.DISABLED)
        thread = threading.Thread(target=run_check, daemon=True)
        thread.start()

    check_button.configure(command=on_check)

    root.mainloop()
