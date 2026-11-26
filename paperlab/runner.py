import hashlib
import json
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path

from .core import (NY, TERMINAL, timestamp, number, eligible, checked_quote,
                   momentum, limit_price, estimated_cost)


class Journal:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS plans (day TEXT PRIMARY KEY, body TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS orders (id TEXT PRIMARY KEY, day TEXT NOT NULL,
                payload TEXT NOT NULL, state TEXT NOT NULL, response TEXT);
            CREATE TABLE IF NOT EXISTS snapshots (seq INTEGER PRIMARY KEY, body TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY, body TEXT NOT NULL);
        ''')
        self.db.commit()

    @contextmanager
    def exclusive(self):
        lock = sqlite3.connect(str(self.path) + ".lock", timeout=0)
        try:
            lock.execute("BEGIN EXCLUSIVE")
            yield
        finally:
            lock.rollback()
            lock.close()

    def meta(self, key, value=None):
        if value is not None:
            with self.db:
                self.db.execute("INSERT OR REPLACE INTO meta VALUES (?, ?)", (key, json.dumps(value)))
        row = self.db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def append(self, table, value):
        if table not in {"snapshots", "events"}:
            raise ValueError("Invalid journal table")
        with self.db:
            self.db.execute(f"INSERT INTO {table}(body) VALUES (?)", (json.dumps(value),))

    def orders(self):
        return list(self.db.execute("SELECT * FROM orders ORDER BY day, id"))

    def update(self, client_id, state, response=None):
        with self.db:
            self.db.execute("UPDATE orders SET state=?, response=? WHERE id=?",
                            (state, json.dumps(response) if response else None, client_id))


class Runner:
    def __init__(self, broker, journal, config):
        self.broker, self.journal, self.config = broker, journal, config

    def tick(self):
        with self.journal.exclusive():
            return self._tick()

    def _tick(self):
        b, j, c = self.broker, self.journal, self.config
        configuration = json.loads(json.dumps(asdict(c)))
        if j.meta("config") not in (None, configuration):
            raise ValueError("Config changed: use a fresh dedicated paper account and state file")
        account = b.account()
        if account.get("status") != "ACTIVE" or account.get("trading_blocked") or account.get("account_blocked"):
            raise ValueError("Paper account is not active for trading")
        if j.meta("account_id") not in (None, account["id"]):
            raise ValueError("Account does not match this journal")
        j.meta("account_id", account["id"])
        j.meta("config", configuration)
        # Reconcile every nonterminal order before making any new decision.
        for row in j.orders():
            if row["state"] in TERMINAL or row["state"] in {"ready", "abandoned"}:
                continue
            order = b.order(row["id"])
            if order is None:
                raise ValueError(f"Uncertain submission {row['id']}: inspect paper dashboard; no automatic retry")
            j.update(row["id"], order["status"], order)
        known = {row["id"] for row in j.orders()}
        if any(o["client_order_id"] not in known for o in b.open_orders()):
            raise ValueError("Unmanaged open orders: use a dedicated paper account")
        positions = {p["symbol"]: number(p["qty"]) for p in b.positions()}
        expected = {}
        for row in j.orders():
            if row["response"]:
                order = json.loads(row["response"])
                sign = 1 if order["side"] == "buy" else -1
                expected[order["symbol"]] = expected.get(order["symbol"], 0) + sign * number(order.get("filled_qty", 0))
        if any(abs(positions.get(s, 0) - expected.get(s, 0)) > 1e-6 for s in positions.keys() | expected.keys()):
            raise ValueError("Position mismatch: external trade, corporate action, or fill race; reconcile before continuing")
        if any(q < 0 or abs(q - round(q)) > 1e-6 for q in positions.values()):
            raise ValueError("Only whole-share long positions are supported")
        clock = b.clock()
        now = timestamp(clock["timestamp"])
        day = now.astimezone(NY).date().isoformat()
        j.append("snapshots", {"timestamp": now.isoformat(), "equity": number(account["equity"]),
                               "cash": number(account["cash"]), "positions": positions, "feed": c.feed})
        if j.meta("initial_equity") is None:
            j.meta("initial_equity", number(account["equity"]))
        # Ready orders from a missed session must never be sent on another day.
        for row in j.orders():
            if row["state"] == "ready" and row["day"] != day:
                j.update(row["id"], "abandoned")
        calendar = b.calendar((now.date() - timedelta(days=max(120, c.lookback * 3))).isoformat(), day)
        calendar = sorted(calendar, key=lambda s: s["date"])
        today = next((s for s in calendar if s["date"] == day), None)
        if not today or not eligible(clock, today, c):
            return "Outside regular-session entry window; reconciled only"
        if any(r["state"] not in TERMINAL | {"ready", "abandoned"} for r in j.orders()):
            return "Waiting for existing orders to finish"
        if not j.db.execute("SELECT 1 FROM plans WHERE day=?", (day,)).fetchone():
            previous = j.db.execute("SELECT MAX(day) FROM plans").fetchone()[0]
            if previous and sum(previous < s["date"] <= day for s in calendar) < c.rebalance_sessions:
                return "Between rebalance sessions"
            dates = [s["date"] for s in calendar if s["date"] < day][-c.lookback - 1:]
            if len(dates) != c.lookback + 1:
                raise ValueError("Insufficient calendar history")
            end = datetime.fromisoformat(day).replace(tzinfo=NY).isoformat()
            bars = b.bars(c.symbols, dates[0], end)
            quotes = b.quotes(c.symbols)
            now = timestamp(b.clock()["timestamp"])
            budget = min(c.capital, number(account["equity"]))
            plan, payloads = {}, []
            for symbol in c.symbols:
                asset = b.asset(symbol)
                if not asset.get("tradable") or asset.get("status") != "active" or asset.get("class") != "us_equity":
                    raise ValueError(f"{symbol} is not an active tradable US equity")
                score = momentum(bars[symbol], dates)
                bid, ask = checked_quote(quotes[symbol], now, c)
                buy_limit = limit_price("buy", bid, ask, c)
                target = int(budget * c.position_fraction / float(buy_limit)) if score > 0 else 0
                delta = target - int(round(positions.get(symbol, 0)))
                plan[symbol] = {"momentum": score, "target": target, "quote": quotes[symbol], "bars": bars[symbol]}
                if not delta:
                    continue
                side = "buy" if delta > 0 else "sell"
                price = limit_price(side, bid, ask, c)
                qty = min(abs(delta), int(c.max_order_dollars / float(price)))
                if qty < 1:
                    continue
                client_id = "pl-" + hashlib.sha256(f"{account['id']}:{day}:{symbol}".encode()).hexdigest()[:32]
                payloads.append({"symbol": symbol, "qty": str(qty), "side": side,
                                 "type": "limit", "limit_price": str(price), "time_in_force": "day",
                                 "extended_hours": False, "client_order_id": client_id})
            with j.db:
                j.db.execute("INSERT INTO plans VALUES (?, ?)", (day, json.dumps(plan)))
                for p in payloads:
                    j.db.execute("INSERT INTO orders VALUES (?, ?, ?, 'ready', NULL)",
                                 (p["client_order_id"], day, json.dumps(p)))
        # Sell orders precede buys. Buys never rely on not-yet-filled sale proceeds.
        ready = [r for r in j.orders() if r["state"] == "ready" and r["day"] == day]
        ready.sort(key=lambda r: json.loads(r["payload"])["side"] == "buy")
        remaining_cash = max(0, number(b.account()["cash"]))
        for row in ready:
            p = json.loads(row["payload"])
            quote = b.quotes([p["symbol"]])[p["symbol"]]
            current_clock = b.clock()
            if not eligible(current_clock, today, c):
                break
            checked_quote(quote, timestamp(current_clock["timestamp"]), c)
            reserve = number(p["qty"]) * number(p["limit_price"])
            reserve += c.commission_per_order + number(p["qty"]) * c.commission_per_share
            if p["side"] == "buy" and reserve > remaining_cash:
                j.update(row["id"], "abandoned")
                j.append("events", {"order": row["id"], "reason": "Insufficient cash; no margin borrowing"})
                continue
            # Commit BEFORE the network request. An ambiguous failure is never retried blindly.
            j.update(row["id"], "attempted")
            response = b.submit(p)
            j.update(row["id"], response["status"], response)
            if p["side"] == "buy":
                remaining_cash -= reserve
        return "Rebalance processed"


def report(journal, config):
    orders = []
    costs = 0
    for row in journal.orders():
        order = json.loads(row["response"]) if row["response"] else json.loads(row["payload"])
        estimate = estimated_cost(order, config)
        costs += estimate
        orders.append({"client_order_id": row["id"], "state": row["state"], **order, "additional_cost_estimate": estimate})
    snapshots = [json.loads(r[0]) for r in journal.db.execute("SELECT body FROM snapshots ORDER BY seq")]
    initial = journal.meta("initial_equity")
    latest = snapshots[-1]["equity"] if snapshots else None
    return {"mode": journal.meta("mode") or "PAPER SIMULATION", "feed": config.feed, "config": asdict(config),
            "initial_account_equity": initial, "latest_account_equity": latest,
            "additional_cost_estimate": costs,
            "adjusted_pnl_estimate": latest - initial - costs if latest is not None else None,
            "orders": orders, "snapshots": snapshots,
            "limitations": [
                "IEX is a single-exchange feed, not consolidated SIP/NBBO." if config.feed == "iex" else "SIP entitlement required.",
                "Alpaca simulates fills; liquidity, queue position, latency, and market impact are not realistic.",
                "Dividends are omitted by Alpaca paper trading. This report is NOT total return.",
                "Splits/external position changes halt trading on reconciliation mismatch; automatic corporate-action accounting is not implemented.",
                "No shorting, options, leverage, extended hours, or cash-account settlement model. Broker paper account rules apply.",
                "Fees are user-configured incremental estimates, not a verified current fee schedule. Extra slippage is a sensitivity assumption.",
                "PnL is account-level: use a dedicated paper account without deposits, withdrawals, resets, or manual trades.",
                "Example momentum strategy is unvalidated; this runner is forward testing, not a historical backtester."]}
