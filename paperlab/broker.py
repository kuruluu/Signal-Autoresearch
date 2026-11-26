"""Small REST adapter; deliberately has no live-trading URL setting."""
import json
from .credentials import read_credentials
from urllib.request import Request, urlopen
from urllib.parse import urlencode, quote
from urllib.error import HTTPError

PAPER = "https://paper-api.alpaca.markets"
DATA = "https://data.alpaca.markets"


class ApiError(RuntimeError):
    def __init__(self, status, path):
        self.status = status
        super().__init__(f"Alpaca HTTP {status} at {path}; check credentials, permissions, or broker dashboard")


class Alpaca:
    def __init__(self, feed="iex"):
        self.feed = feed
        credentials = read_credentials()
        self.key = credentials.get("APCA_API_KEY_ID")
        self.secret = credentials.get("APCA_API_SECRET_KEY")
        if not self.key or not self.secret:
            raise ValueError("Set paper credentials in environment variables or the project's ignored .env file")

    def request(self, path, params=None, body=None, data=False):
        url = (DATA if data else PAPER) + path
        if params:
            url += "?" + urlencode(params)
        req = Request(url, data=json.dumps(body).encode() if body is not None else None,
                      headers={"APCA-API-KEY-ID": self.key, "APCA-API-SECRET-KEY": self.secret,
                               "Content-Type": "application/json"})
        try:
            with urlopen(req, timeout=20) as response:
                return json.load(response)
        except HTTPError as exc:
            raise ApiError(exc.code, path) from None

    def account(self):
        return self.request("/v2/account")

    def clock(self):
        return self.request("/v2/clock")

    def calendar(self, start, end):
        return self.request("/v2/calendar", {"start": start, "end": end})

    def positions(self):
        return self.request("/v2/positions")

    def open_orders(self):
        return self.request("/v2/orders", {"status": "open", "limit": 500})

    def asset(self, symbol):
        return self.request("/v2/assets/" + quote(symbol, safe=""))

    def order(self, client_id):
        try:
            return self.request("/v2/orders:by_client_order_id", {"client_order_id": client_id})
        except ApiError as exc:
            if exc.status == 404:
                return None
            raise

    def submit(self, payload):
        return self.request("/v2/orders", body=payload)

    def quotes(self, symbols):
        return self.request("/v2/stocks/quotes/latest", {"symbols": ",".join(symbols), "feed": self.feed}, data=True)["quotes"]

    def bars(self, symbols, start, end):
        params = {"symbols": ",".join(symbols), "timeframe": "1Day", "start": start,
                  "end": end, "adjustment": "split", "feed": self.feed, "sort": "asc", "limit": 10000}
        result = {symbol: [] for symbol in symbols}
        seen = set()
        while True:
            page = self.request("/v2/stocks/bars", params, data=True)
            for symbol, rows in (page.get("bars") or {}).items():
                result.setdefault(symbol, []).extend(rows)
            token = page.get("next_page_token")
            if not token:
                return result
            if token in seen:
                raise ValueError("Repeated pagination token")
            seen.add(token)
            params["page_token"] = token
