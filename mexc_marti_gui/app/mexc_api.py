import hashlib
import hmac
import math
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

    def get_exchange_info(self, symbol: str) -> tuple[float, float]:
        url = f"{self.base_url}/api/v3/exchangeInfo"
        try:
            response = requests.get(url, params={"symbol": symbol}, timeout=10)
        except requests.RequestException as exc:
            raise ValueError(f"Ошибка запроса exchangeInfo: {exc}") from exc
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
            raise ValueError("Некорректный ответ exchangeInfo от MEXC") from exc

        symbols = payload.get("symbols")
        if not symbols:
            raise ValueError("Не удалось получить данные символа из exchangeInfo")
        filters = symbols[0].get("filters", [])
        tick_size = None
        step_size = None
        for item in filters:
            if item.get("filterType") == "PRICE_FILTER":
                tick_size = float(item.get("tickSize", 0))
            if item.get("filterType") == "LOT_SIZE":
                step_size = float(item.get("stepSize", 0))
        if not tick_size or not step_size:
            raise ValueError("Не удалось определить шаг цены/количества")
        return tick_size, step_size

    def round_price(self, price: float, tick_size: float) -> float:
        return math.floor(price / tick_size) * tick_size

    def round_qty(self, qty: float, step_size: float) -> float:
        return math.floor(qty / step_size) * step_size

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

    def get_account(self) -> dict:
        return self._signed_request("GET", "/api/v3/account")

    def get_open_orders(self, symbol: str) -> list:
        return self._signed_request("GET", "/api/v3/openOrders", {"symbol": symbol})

    def get_order(self, symbol: str, order_id: str) -> dict:
        return self._signed_request(
            "GET", "/api/v3/order", {"symbol": symbol, "orderId": order_id}
        )

    def cancel_order(self, symbol: str, order_id: str) -> dict:
        return self._signed_request(
            "DELETE", "/api/v3/order", {"symbol": symbol, "orderId": order_id}
        )

    def cancel_all_orders(self, symbol: str) -> list:
        results = []
        try:
            open_orders = self.get_open_orders(symbol)
        except ValueError:
            return results
        for order in open_orders:
            order_id = order.get("orderId")
            if not order_id:
                continue
            try:
                results.append(self.cancel_order(symbol, str(order_id)))
            except ValueError:
                continue
        return results

    def place_limit_buy(self, symbol: str, price: float, quantity: float) -> dict:
        return self._signed_request(
            "POST",
            "/api/v3/order",
            {
                "symbol": symbol,
                "side": "BUY",
                "type": "LIMIT",
                "timeInForce": "GTC",
                "price": f"{price:.8f}",
                "quantity": f"{quantity:.8f}",
            },
        )

    def place_limit_sell(self, symbol: str, price: float, quantity: float) -> dict:
        return self._signed_request(
            "POST",
            "/api/v3/order",
            {
                "symbol": symbol,
                "side": "SELL",
                "type": "LIMIT",
                "timeInForce": "GTC",
                "price": f"{price:.8f}",
                "quantity": f"{quantity:.8f}",
            },
        )

    def _signed_request(self, method: str, path: str, params: dict | None = None) -> dict:
        if params is None:
            params = {}
        params["timestamp"] = int(time.time() * 1000)
        query_string = urllib.parse.urlencode(params)
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        params["signature"] = signature

        headers = {"X-MEXC-APIKEY": self.api_key}
        url = f"{self.base_url}{path}"
        try:
            response = requests.request(
                method, url, params=params, headers=headers, timeout=10
            )
        except requests.RequestException as exc:
            raise ValueError(f"Ошибка запроса к MEXC: {exc}") from exc

        if not response.ok:
            message = response.text.strip()
            try:
                payload = response.json()
                message = payload.get("msg") or payload.get("message") or message
            except ValueError:
                pass
            raise ValueError(message or f"HTTP {response.status_code}")

        try:
            return response.json()
        except ValueError as exc:
            raise ValueError("Некорректный ответ MEXC") from exc

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
