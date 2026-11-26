import json
from dataclasses import replace
from datetime import datetime
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from paperlab.core import Config, checked_quote, eligible, estimated_cost, momentum, timestamp
from paperlab.demo import DemoBroker
from paperlab.runner import Journal, Runner, report
from paperlab.broker import Alpaca, PAPER


class SimulationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.journal = Journal(Path(self.temp.name) / "state.sqlite")
        self.broker = DemoBroker()
        self.config = Config()
        self.runner = Runner(self.broker, self.journal, self.config)

    def tearDown(self):
        self.journal.db.close()
        self.temp.cleanup()

    def test_restart_does_not_duplicate_orders(self):
        self.runner.tick()
        count = self.broker.submissions
        Runner(self.broker, self.journal, self.config).tick()
        self.assertEqual(count, 3)
        self.assertEqual(count, self.broker.submissions)

    def test_timeout_after_accept_recovers_without_duplicate(self):
        self.broker.timeout_after_accept = True
        with self.assertRaises(TimeoutError):
            self.runner.tick()
        self.runner.tick()
        self.assertEqual(self.broker.submissions, 3)

    def test_unknown_submission_is_not_retried(self):
        with patch.object(self.broker, "submit", side_effect=TimeoutError):
            with self.assertRaises(TimeoutError):
                self.runner.tick()
        with self.assertRaisesRegex(ValueError, "Uncertain submission"):
            self.runner.tick()
        self.assertEqual(self.broker.submissions, 0)

    def test_stale_quote_blocks_plan(self):
        quotes = self.broker.quotes(self.config.symbols)
        quotes["SPY"]["t"] = "2020-01-01T10:00:00-05:00"
        with patch.object(self.broker, "quotes", return_value=quotes):
            with self.assertRaisesRegex(ValueError, "Stale"):
                self.runner.tick()
        self.assertEqual(len(self.journal.orders()), 0)

    def test_future_bar_cannot_change_signal(self):
        bars = [{"t": "2026-10-01T04:00:00Z", "c": 100, "v": 1},
                {"t": "2026-10-02T04:00:00Z", "c": 110, "v": 1},
                {"t": "2026-10-05T04:00:00Z", "c": 1, "v": 1}]
        self.assertAlmostEqual(momentum(bars, ["2026-10-01", "2026-10-02"]), .1)
        with self.assertRaisesRegex(ValueError, "Missing"):
            momentum(bars[:1], ["2026-10-01", "2026-10-02"])

    def test_early_close_and_dst(self):
        c = replace(self.config, minutes_after_open=0, entry_window_minutes=400)
        session = {"date": "2026-11-27", "open": "09:30", "close": "13:00"}
        self.assertTrue(eligible({"timestamp": "2026-11-27T17:59:00Z", "is_open": True}, session, c))
        self.assertFalse(eligible({"timestamp": "2026-11-27T18:00:00Z", "is_open": True}, session, c))
        self.assertFalse(eligible({"timestamp": "2026-11-27T13:30:00Z", "is_open": True}, session, c))

    def test_closed_market_no_submission(self):
        clock = {**self.broker.clock(), "is_open": False}
        with patch.object(self.broker, "clock", return_value=clock):
            self.runner.tick()
        self.assertEqual(self.broker.submissions, 0)

    def test_partial_fill_cost_is_cumulative_not_double_counted(self):
        c = replace(self.config, commission_per_order=1, commission_per_share=.01, extra_slippage_bps=10)
        o = {"side": "buy", "filled_qty": "5", "filled_avg_price": "100"}
        self.assertAlmostEqual(estimated_cost(o, c), 1.55)
        o["filled_qty"] = "10"
        self.assertAlmostEqual(estimated_cost(o, c), 2.1)

    def test_position_mismatch_halts(self):
        self.broker.holdings["SPY"] = 1
        with self.assertRaisesRegex(ValueError, "Position mismatch"):
            self.runner.tick()

    def test_rebalance_waits_five_sessions(self):
        self.runner.tick()
        self.broker.index += 4
        self.assertEqual(self.runner.tick(), "Between rebalance sessions")
        self.broker.index += 1
        self.assertEqual(self.runner.tick(), "Rebalance processed")

    def test_config_change_rejected(self):
        self.runner.tick()
        with self.assertRaisesRegex(ValueError, "Config changed"):
            Runner(self.broker, self.journal, replace(self.config, lookback=10)).tick()

    def test_cash_never_negative(self):
        self.broker.cash = 100
        self.runner.tick()
        self.assertGreaterEqual(self.broker.cash, 0)

    def test_crossed_and_nan_quotes_rejected(self):
        q = self.broker.quotes(["SPY"])["SPY"]
        for bid in (q["ap"] + 1, float("nan")):
            with self.assertRaises(ValueError):
                checked_quote({**q, "bp": bid}, timestamp(q["t"]), self.config)

    def test_report_costs_do_not_accumulate_on_repeated_reads(self):
        self.runner.tick()
        a = report(self.journal, self.config)
        b = report(self.journal, self.config)
        self.assertGreater(a["additional_cost_estimate"], 0)
        self.assertEqual(a, b)

    def test_paper_endpoint_is_fixed(self):
        self.assertEqual(PAPER, "https://paper-api.alpaca.markets")

    def test_invalid_config(self):
        for args in ({"capital": float("nan")}, {"symbols": ["SPY", "SPY"]}, {"position_fraction": .5}):
            with self.assertRaises(ValueError):
                Config(**args)

    def test_partial_fill_blocks_remaining_orders_then_reconciles(self):
        original = self.broker.submit
        def partial(payload):
            order = original({**payload, "qty": "1"})
            order["status"] = "partially_filled"
            return order
        with patch.object(self.broker, "submit", side_effect=partial):
            self.runner.tick()
        count = self.broker.submissions
        self.assertEqual(self.runner.tick(), "Waiting for existing orders to finish")
        self.assertEqual(count, self.broker.submissions)
        for order in self.broker.orders.values():
            order["status"] = "canceled"
        self.runner.tick()
        self.assertTrue(all(r["state"] == "canceled" for r in self.journal.orders()))

    def test_restart_from_disk(self):
        self.runner.tick()
        path = self.journal.path
        self.journal.db.close()
        self.journal = Journal(path)
        Runner(self.broker, self.journal, self.config).tick()
        self.assertEqual(self.broker.submissions, 3)

    def test_concurrent_runner_cannot_enter(self):
        import sqlite3
        other = Journal(self.journal.path)
        try:
            with self.journal.exclusive():
                with self.assertRaises(sqlite3.OperationalError):
                    Runner(self.broker, other, self.config).tick()
            self.assertEqual(self.broker.submissions, 0)
        finally:
            other.db.close()

    def test_paginated_bars_are_all_loaded(self):
        with patch.dict("os.environ", {"APCA_API_KEY_ID": "test", "APCA_API_SECRET_KEY": "test"}):
            broker = Alpaca()
        pages = [{"bars": {"SPY": [{"c": 1}]}, "next_page_token": "next"},
                 {"bars": {"SPY": [{"c": 2}]}, "next_page_token": None}]
        with patch.object(broker, "request", side_effect=pages) as request:
            bars = broker.bars(["SPY"], "2026-10-01", "2026-10-03")
        self.assertEqual(bars["SPY"], [{"c": 1}, {"c": 2}])
        self.assertEqual(request.call_count, 2)

    def test_changed_account_rejected(self):
        self.runner.tick()
        account = {**self.broker.account(), "id": "OTHER"}
        with patch.object(self.broker, "account", return_value=account):
            with self.assertRaisesRegex(ValueError, "Account does not match"):
                self.runner.tick()


if __name__ == "__main__":
    unittest.main()
