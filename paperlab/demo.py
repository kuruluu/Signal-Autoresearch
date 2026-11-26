"""Deterministic synthetic broker for demonstrations and failure tests."""
from datetime import date, datetime, timedelta
from .core import NY


class DemoBroker:
    def __init__(self):
        self.days = []
        day = date(2026, 8, 3)
        while len(self.days) < 70:
            if day.weekday() < 5:
                self.days.append(day.isoformat())
            day += timedelta(days=1)
        self.index = 30
        self.cash = 10000.0
        self.holdings = {}
        self.orders = {}
        self.submissions = 0
        self.timeout_after_accept = False

    def price(self, index=None):
        index = self.index if index is None else index
        return 100 + index if index < 35 else 135 - (index - 35) * 4

    def account(self):
        return {"id": "SYNTHETIC-DEMO", "status": "ACTIVE", "cash": str(self.cash),
                "equity": str(self.cash + sum(self.holdings.values()) * self.price())}

    def clock(self):
        return {"timestamp": self.days[self.index] + "T10:00:00-04:00", "is_open": True}

    def calendar(self, start, end):
        return [{"date": d, "open": "09:30", "close": "16:00"} for d in self.days if start <= d <= end]

    def asset(self, symbol):
        return {"tradable": True, "status": "active", "class": "us_equity"}

    def positions(self):
        return [{"symbol": s, "qty": str(q)} for s, q in self.holdings.items() if q]

    def open_orders(self):
        return []

    def order(self, client_id):
        return self.orders.get(client_id)

    def quotes(self, symbols):
        return {s: {"t": self.clock()["timestamp"], "bp": self.price() - .01,
                    "ap": self.price() + .01, "bs": 100, "as": 100} for s in symbols}

    def bars(self, symbols, start, end):
        return {s: [{"t": datetime.fromisoformat(d).replace(tzinfo=NY).isoformat(),
                     "c": self.price(i), "v": 100000} for i, d in enumerate(self.days)
                    if start <= d < self.days[self.index]] for s in symbols}

    def submit(self, payload):
        self.submissions += 1
        qty = int(payload["qty"])
        sign = 1 if payload["side"] == "buy" else -1
        price = self.price() + sign * .01
        self.cash -= sign * qty * price
        self.holdings[payload["symbol"]] = self.holdings.get(payload["symbol"], 0) + sign * qty
        order = {**payload, "status": "filled", "filled_qty": str(qty), "filled_avg_price": str(price)}
        self.orders[payload["client_order_id"]] = order
        if self.timeout_after_accept:
            self.timeout_after_accept = False
            raise TimeoutError("Synthetic timeout after broker accepted order")
        return order
