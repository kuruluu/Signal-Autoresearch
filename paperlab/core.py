from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_FLOOR, ROUND_CEILING
from zoneinfo import ZoneInfo
import math

NY = ZoneInfo("America/New_York")
TERMINAL = {"filled", "canceled", "expired", "rejected", "replaced"}


def timestamp(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Timestamp must include timezone")
    return result


def number(value):
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("Non-finite numeric data")
    return result


@dataclass(frozen=True)
class Config:
    symbols: tuple = ("SPY", "QQQ", "IWM")
    feed: str = "iex"
    capital: float = 10000
    lookback: int = 20
    rebalance_sessions: int = 5
    position_fraction: float = .25
    max_order_dollars: float = 2500
    max_quote_age_seconds: float = 30
    max_spread_bps: float = 30
    limit_buffer_bps: float = 2
    minutes_after_open: int = 10
    entry_window_minutes: int = 30
    poll_seconds: int = 60
    commission_per_share: float = 0
    commission_per_order: float = 0
    sell_fee_per_share: float = 0
    sell_fee_bps: float = 0
    extra_slippage_bps: float = 5

    def __post_init__(self):
        object.__setattr__(self, "symbols", tuple(self.symbols))
        if not self.symbols or len(set(self.symbols)) != len(self.symbols):
            raise ValueError("Symbols must be nonempty and unique")
        if any(not s.isalpha() or not s.isupper() for s in self.symbols):
            raise ValueError("Use uppercase ETF symbols")
        if self.feed not in {"iex", "sip"}:
            raise ValueError("Feed must be iex or sip")
        for key, value in asdict(self).items():
            if key not in {"symbols", "feed"} and number(value) < 0:
                raise ValueError(f"{key} must be nonnegative")
        for key in ("lookback", "rebalance_sessions", "entry_window_minutes", "poll_seconds"):
            value = getattr(self, key)
            if not isinstance(value, int) or value < 1:
                raise ValueError(f"{key} must be a positive integer")
        if not 0 < self.position_fraction * len(self.symbols) <= .95:
            raise ValueError("Total allocation must be positive and at most 95%")
        if self.capital <= 0 or self.max_order_dollars <= 0 or self.limit_buffer_bps >= 10000:
            raise ValueError("Invalid capital, order cap, or price buffer")


def session_bounds(session):
    return tuple(datetime.fromisoformat(f"{session['date']}T{session[k]}").replace(tzinfo=NY)
                 for k in ("open", "close"))


def eligible(clock, session, config):
    now = timestamp(clock["timestamp"])
    start, close = session_bounds(session)
    start += timedelta(minutes=config.minutes_after_open)
    end = min(close, start + timedelta(minutes=config.entry_window_minutes))
    return clock["is_open"] is True and start <= now < end


def checked_quote(quote, now, config):
    age = (now - timestamp(quote["t"])).total_seconds()
    bid, ask = number(quote["bp"]), number(quote["ap"])
    if not -2 <= age <= config.max_quote_age_seconds:
        raise ValueError("Stale or future quote")
    if bid <= 0 or ask < bid or number(quote["bs"]) <= 0 or number(quote["as"]) <= 0:
        raise ValueError("Invalid, crossed, or empty quote")
    if (ask - bid) / ((ask + bid) / 2) * 10000 > config.max_spread_bps:
        raise ValueError("Spread exceeds configured maximum")
    return bid, ask


def momentum(bars, expected_dates):
    """Only complete, contiguous prior sessions enter the signal."""
    closes = {}
    for bar in bars:
        day = timestamp(bar["t"]).astimezone(NY).date().isoformat()
        if day not in expected_dates:
            continue
        if day in closes:
            raise ValueError("Duplicate daily bar")
        price = number(bar["c"])
        if price <= 0 or number(bar["v"]) <= 0:
            raise ValueError("Invalid daily bar")
        closes[day] = price
    if set(closes) != set(expected_dates):
        raise ValueError("Missing completed-session bars")
    return closes[expected_dates[-1]] / closes[expected_dates[0]] - 1


def limit_price(side, bid, ask, config):
    price = (ask * (1 + config.limit_buffer_bps / 10000) if side == "buy"
             else bid * (1 - config.limit_buffer_bps / 10000))
    # Round toward a stricter limit, never beyond the requested buffer.
    return Decimal(str(price)).quantize(Decimal(".01"), rounding=ROUND_FLOOR if side == "buy" else ROUND_CEILING)


def estimated_cost(order, config):
    qty = number(order.get("filled_qty", 0))
    price = number(order.get("filled_avg_price") or 0)
    if qty <= 0:
        return 0.0
    cost = config.commission_per_order + qty * config.commission_per_share
    if order["side"] == "sell":
        cost += qty * config.sell_fee_per_share + qty * price * config.sell_fee_bps / 10000
    return cost + qty * price * config.extra_slippage_bps / 10000
