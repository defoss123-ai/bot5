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
