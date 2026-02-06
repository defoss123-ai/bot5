import tkinter as tk

from .logger import get_logger


def run_app() -> None:
    logger = get_logger()
    logger.info("UI started")

    root = tk.Tk()
    root.title("MEXC Спотовый Мартингейл-бот")

    label = tk.Label(root, text="Шаг 0: каркас готов")
    label.pack(padx=20, pady=10)

    exit_button = tk.Button(root, text="Выход", command=root.destroy)
    exit_button.pack(pady=10)

    root.mainloop()
