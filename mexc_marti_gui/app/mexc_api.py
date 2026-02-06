import hashlib
import hmac
import time
import urllib.parse

import requests


class MexcClient:
    def __init__(self, api_key: str, api_secret: str, base_url: str) -> None:
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip("/")

    def get_price(self, symbol: str) -> float:
        url = f"{self.base_url}/api/v3/ticker/price"
        try:
            response = requests.get(url, params={"symbol": symbol}, timeout=10)
        except requests.RequestException as exc:
            raise ValueError(f"Ошибка запроса цены: {exc}") from exc
        if not response.ok:
            message = response.text.strip()
            try:
                payload = response.json()
                message = payload.get("msg") or payload.get("message") or message
            except ValueError:
                pass
            raise ValueError(message or f"HTTP {response.status_code}")

        try:
            payload = response.json()
        except ValueError as exc:
            raise ValueError("Некорректный ответ цены от MEXC") from exc

        price_raw = payload.get("price")
        if price_raw is None:
            raise ValueError("В ответе MEXC отсутствует цена")

        try:
            return float(price_raw)
        except (TypeError, ValueError) as exc:
            raise ValueError("Некорректный формат цены от MEXC") from exc

    def get_klines(self, symbol: str, interval: str, limit: int = 200) -> list:
        url = f"{self.base_url}/api/v3/klines"
        try:
            response = requests.get(
                url,
                params={"symbol": symbol, "interval": interval, "limit": limit},
                timeout=10,
            )
        except requests.RequestException as exc:
            raise ValueError(f"Ошибка запроса свечей: {exc}") from exc
        if not response.ok:
            message = response.text.strip()
            try:
                payload = response.json()
                message = payload.get("msg") or payload.get("message") or message
            except ValueError:
                pass
            raise ValueError(message or f"HTTP {response.status_code}")

        try:
            payload = response.json()
        except ValueError as exc:
            raise ValueError("Некорректный ответ свечей от MEXC") from exc

        if not isinstance(payload, list) or not payload:
            raise ValueError("Пустой ответ свечей от MEXC")

        return payload

    def check_connection(self) -> tuple[bool, str]:
        timestamp = int(time.time() * 1000)
        params = {"timestamp": timestamp}
        query_string = urllib.parse.urlencode(params)
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        params["signature"] = signature

        headers = {"X-MEXC-APIKEY": self.api_key}
        url = f"{self.base_url}/api/v3/account"

        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
        except requests.RequestException as exc:
            return False, str(exc)

        if response.ok:
            return True, "OK"

        message = response.text.strip()
        try:
            payload = response.json()
            message = payload.get("msg") or payload.get("message") or message
        except ValueError:
            pass
        return False, message or f"HTTP {response.status_code}"
