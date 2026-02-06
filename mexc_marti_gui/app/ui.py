import tkinter as tk
from tkinter import messagebox

from .logger import get_logger
from .mexc_api import MexcClient


def run_app() -> None:
    logger = get_logger()
    logger.info("UI started")

    root = tk.Tk()
    root.title("MEXC Спотовый Мартингейл-бот")

    frame = tk.Frame(root)
    frame.pack(padx=20, pady=20)

    tk.Label(frame, text="API Key").grid(row=0, column=0, sticky="w", pady=5)
    api_key_entry = tk.Entry(frame, width=50)
    api_key_entry.grid(row=0, column=1, pady=5)

    tk.Label(frame, text="API Secret").grid(row=1, column=0, sticky="w", pady=5)
    api_secret_entry = tk.Entry(frame, width=50, show="*")
    api_secret_entry.grid(row=1, column=1, pady=5)

    tk.Label(frame, text="Base URL").grid(row=2, column=0, sticky="w", pady=5)
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

    exit_button = tk.Button(root, text="Выход", command=root.destroy)
    exit_button.pack(pady=10)

    root.mainloop()
