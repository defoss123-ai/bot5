import os

from dotenv import load_dotenv

from app.ui import DEFAULT_BASE_URL, run_app


def main() -> None:
    load_dotenv()
    api_key = os.getenv("API_KEY", "")
    api_secret = os.getenv("API_SECRET", "")
    base_url = os.getenv("MEXC_BASE_URL", DEFAULT_BASE_URL)
    run_app(api_key=api_key, api_secret=api_secret, base_url=base_url)


if __name__ == "__main__":
    main()
