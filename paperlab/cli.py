import argparse
from dataclasses import asdict
import html
import json
from pathlib import Path
import tempfile
import time

from .broker import Alpaca
from .core import Config
from .runner import Journal, Runner, report


def write_report(journal, config, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    result = report(journal, config)
    (directory / "report.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    escape = lambda x: html.escape(str(x))
    rows = "".join("<tr>" + "".join(f"<td>{escape(o.get(k, ''))}</td>" for k in
                   ("symbol", "side", "qty", "filled_qty", "filled_avg_price", "state", "additional_cost_estimate")) + "</tr>"
                   for o in result["orders"])
    warnings = "".join(f"<li>{escape(w)}</li>" for w in result["limitations"])
    page = f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
    <title>ETF Paper Lab</title><style>body{{font:16px system-ui;background:#111a26;color:#e9eff7;max-width:1100px;margin:40px auto;padding:20px}}
    h1{{font-size:36px}}.badge{{color:#7ed9b5}}table{{border-collapse:collapse;width:100%}}td,th{{padding:12px;text-align:left;border-bottom:1px solid #334155}}
    li{{margin:10px 0}}.metrics{{padding:20px;background:#1d2b3d;border-radius:12px}}small{{color:#aab8cc}}</style>
    <p class="badge">{escape(result['mode'])} · CONFIGURED FEED: {escape(config.feed.upper())}</p><h1>ETF Paper Lab</h1>
    <p>Account snapshots and additional execution-cost estimates. Demo results use synthetic data.</p>
    <div class="metrics">Latest account equity: <b>{escape(result['latest_account_equity'])}</b><br>
    Additional estimated costs: <b>{result['additional_cost_estimate']:.2f}</b><br>
    Adjusted P&amp;L estimate: <b>{escape(result['adjusted_pnl_estimate'])}</b></div>
    <h2>Orders</h2><div style="overflow:auto"><table><tr><th>Symbol</th><th>Side</th><th>Requested</th><th>Filled</th><th>Average price</th><th>Status</th><th>Added costs</th></tr>{rows}</table></div>
    <h2>Assumptions and limitations</h2><ul>{warnings}</ul><small>Detailed snapshots, configuration and order IDs are in report.json. Equity is from the last reconciliation snapshot.</small></html>'''
    (directory / "report.html").write_text(page, encoding="utf-8")
    return directory / "report.html"


def main(argv=None):
    parser = argparse.ArgumentParser(description="ETF Paper Lab — paper-only forward testing")
    parser.add_argument("command", choices=["demo", "check", "once", "run", "report"])
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--state", default="state/paper.sqlite")
    parser.add_argument("--output", default="reports/paper")
    args = parser.parse_args(argv)
    config = Config(**json.loads(Path(args.config).read_text(encoding="utf-8-sig")))
    if args.command == "demo":
        from .demo import DemoBroker
        with tempfile.TemporaryDirectory() as temp:
            broker = DemoBroker()
            journal = Journal(Path(temp) / "demo.sqlite")
            journal.meta("mode", "SYNTHETIC DEMO — NO MARKET DATA")
            try:
                runner = Runner(broker, journal, config)
                for i in range(30, 46):
                    broker.index = i
                    runner.tick()
                print("SYNTHETIC DEMO:", write_report(journal, config, "reports/demo"))
            finally:
                journal.db.close()
        return
    if args.command == "report":
        if not Path(args.state).exists():
            parser.error("No state file; run demo or connect a paper account first")
        journal = Journal(args.state)
        try:
            stored = journal.meta("config")
            print(write_report(journal, Config(**stored) if stored else config, args.output))
        finally:
            journal.db.close()
        return
    broker = Alpaca(config.feed)
    if args.command == "check":
        account, clock = broker.account(), broker.clock()
        quotes = broker.quotes(config.symbols)
        print(json.dumps({"endpoint": "paper", "account_status": account["status"], "feed": config.feed,
                          "clock": clock, "quote_timestamps": {s: q["t"] for s, q in quotes.items()}}, indent=2))
        print("Read-only check; no orders submitted. Quote freshness is enforced during trading.")
        return
    journal = Journal(args.state)
    runner = Runner(broker, journal, config)
    try:
        while True:
            try:
                print(runner.tick(), flush=True)
                write_report(journal, config, args.output)
            except Exception as exc:
                journal.append("events", {"error": str(exc), "at": time.time()})
                if args.command == "once":
                    raise
                print(f"No new orders this cycle: {exc}", flush=True)
            if args.command == "once":
                break
            time.sleep(config.poll_seconds)
    finally:
        journal.db.close()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Stopped. Broker-held DAY orders may remain open until filled, canceled, or expired.")
