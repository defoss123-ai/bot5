import hashlib
import hmac
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests

from .logger import get_logger


class MexcClient:
    def __init__(self, api_key: str, api_secret: str, base_url: str) -> None:
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip("/")
        self.logger = get_logger()

    def get_server_time(self) -> Dict[str, Any]:
        return self._request("GET", "/api/v3/time")

    def get_account(self) -> Dict[str, Any]:
        params = {"timestamp": self._timestamp_ms()}
        return self._request("GET", "/api/v3/account", params=params, signed=True)

    def _timestamp_ms(self) -> int:
        return int(time.time() * 1000)

    def _sign(self, params: Dict[str, Any]) -> str:
        query = urlencode(params)
        signature = hmac.new(self.api_secret.encode("utf-8"), query.encode("utf-8"), hashlib.sha256)
        return signature.hexdigest()

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        signed: bool = False,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        params = params or {}

        headers = {}
        if signed:
            params["signature"] = self._sign(params)
            headers["X-MEXC-APIKEY"] = self.api_key

        try:
            response = requests.request(method, url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
        except requests.exceptions.HTTPError as exc:
            self.logger.error("HTTP ошибка при запросе к MEXC: %s", exc)
            try:
                error_payload = response.json()
            except Exception:
                error_payload = {"msg": response.text}
            message = error_payload.get("msg") or error_payload.get("message") or "Неизвестная ошибка API"
            return {"_error": f"Ошибка API: {message}", "_status": response.status_code}
        except requests.exceptions.RequestException as exc:
            self.logger.error("Сетевая ошибка при запросе к MEXC: %s", exc)
            return {"_error": "Сетевая ошибка. Проверьте подключение к интернету и Base URL."}

        try:
            return response.json()
        except ValueError:
            self.logger.error("Не удалось разобрать ответ MEXC как JSON")
            return {"_error": "Некорректный ответ от сервера MEXC."}
