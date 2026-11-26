# Signal Autoresearch

Research objective: reproducible executable market edges across instruments and holding periods, using $10,000 capital and separate maximum-drawdown tiers of 50%, 30%, and 20%. Rank eligible strategies by robust net CAGR after costs and execution constraints. No independently validated executable strategy has been established yet.

Current instructions and evidence are in `SIGNAL_RESEARCH_HANDOFF.txt` and `research/replication_first/RESEARCH_MANDATE.json`. The Alpaca runner below is a narrow paper-only ETF example, not a complete multi-asset execution system. Live trading is unauthorized and 2024–2025 market observations remain sealed.

Research checkpoints contain code, registrations and aggregate findings, including failures. Raw inputs, third-party papers, account logs and credentials are intentionally excluded; rebuilding experiments requires separately obtaining their documented inputs. Use `python -m researchlab.checkpoint --commit --message "Concrete research outcome"` for a checked local checkpoint, and `--push` only after the authorized `kuruluu/Signal-Autoresearch` remote is available.

## ETF paper runner

For the separate 50-paper historical research project, open `research/dashboard.html` and read [the research guide](research/README.md). The reusable continuation file is `SIGNAL_RESEARCH_HANDOFF.txt`. Research code has no broker order access.

A local Python system for **forward-testing ETF strategies against current markets** using Alpaca's paper account. No real-money order endpoint is present. It runs on Python 3.11+ and uses SQLite and the standard library; Windows needs `tzdata` (included in the project dependencies).

## Start here

On this computer, from this directory:

```powershell
.\run.ps1 demo
```

Open `reports/demo/report.html`. The demo uses **synthetic data and an intentionally simple immediate-fill broker** to exercise the workflow. It is not historical market evidence or a realistic fill simulator. It never contacts Alpaca.

For a portable installation:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e .
.\.venv\Scripts\python -m paperlab demo
```

## Connect your free Alpaca account

Use a **dedicated, empty paper account** without manual trades, deposits, withdrawals or resets during a run. Existing positions or unknown orders are rejected. Configure its initial balance to the capital you intend to simulate. `capital` in config.json limits the strategy budget; account-level performance still includes the account's full cash balance.

Set your **paper** credentials in your own local PowerShell terminal. Do not paste keys into chat or commit them:

```powershell
$env:APCA_API_KEY_ID = 'YOUR_PAPER_KEY'
$env:APCA_API_SECRET_KEY = 'YOUR_PAPER_SECRET'
.\run.ps1 check
```

`check` is read-only. It verifies account/data access and displays clock and quote timestamps. Quotes can be old when the market is closed; the runner enforces freshness during its trading window.

`./run.ps1 capabilities` performs read-only paper-account, calendar, historical SIP bars, quotes and trades probes and writes `reports/alpaca_capabilities.json`. It requests only small 2016/2023 samples, preserves the sealed 2024–2025 period, never submits orders, and reports missing credentials explicitly. Configure credentials in the same terminal where this command runs. A successful sample does not establish complete historical or delisted-security coverage.

To make credentials available to local research commands in other processes, save the two variables in this project's `.env` file. It is ignored by Git and contains local plaintext credentials; never commit or share it. The adapter reads only `APCA_API_KEY_ID` and `APCA_API_SECRET_KEY`, with process variables taking precedence, and never evaluates file content. From the terminal where your paper credentials are already configured:

```powershell
if (-not $env:APCA_API_KEY_ID -or -not $env:APCA_API_SECRET_KEY) { throw 'Set both paper credentials first.' }
@("APCA_API_KEY_ID=$env:APCA_API_KEY_ID", "APCA_API_SECRET_KEY=$env:APCA_API_SECRET_KEY") | Set-Content -LiteralPath .env -Encoding utf8
```

```powershell
.\run.ps1 once    # One cycle; may submit simulated orders during the entry window
.\run.ps1 run     # Keep running in the foreground, polling every 60 seconds
.\run.ps1 report  # Rebuild reports from saved state without broker access
```

The computer must stay awake and connected for continuous operation. Stopping the program does not cancel broker-held orders. DAY orders can continue to fill in their eligible session; inspect/cancel them in Alpaca's paper dashboard when necessary. The process does not install scheduled tasks or background services.

## Included strategy and timing

The example checks 20-session price momentum in SPY, QQQ and IWM, using split-adjusted daily bars through the previous completed session. Positive momentum targets 25% of configured capital per ETF; otherwise the target is zero. Cash is retained for inactive signals. These overlapping equity ETFs are a software example, not a validated or diversified recommendation.

Rebalancing occurs every five **exchange sessions**, within the window 10–40 minutes after the official open. A position can stay open longer than five days if the signal remains positive. Missed rebalances run at the next eligible window. No intraday stops are implemented.

Orders are whole-share, long-only, regular-session DAY limits. Buys use ask plus a configurable buffer; sells use bid minus a buffer, rounded toward the stricter limit. Limits do not guarantee execution. Maximum order size is capped; the cap may leave a target only partly reached until the next rebalance. Rejected, canceled or expired orders are not automatically replaced that day. No position is assumed filled merely because submission succeeded.

Edit `config.json` before starting. To implement another strategy, replace `momentum()` and the target calculation in `paperlab/runner.py`; keep data validation, the journal, and broker adapter intact. Preserve the previous-session cutoff. Use a fresh empty paper account and a new `--state` file when changing strategy/configuration; the journal prevents mixing experiments.

## Data and execution coverage

| Item | Behavior |
|---|---|
| Current data | Alpaca IEX by default; SIP can be configured if your account has access |
| Data provenance | Signal bars and quotes saved in each SQLite plan; feed/configuration persisted |
| Data quality | Reject missing/duplicate session bars, non-finite prices, zero volume, stale/future/crossed quotes and excessive spreads |
| Holidays, early closes, daylight saving | Broker calendar and clock; timezone-aware New York session boundaries |
| Orders and partial fills | Alpaca paper broker; persisted states reconciled on subsequent cycles |
| Restart/retry | Durable client IDs; intent committed before submission; uncertain submissions looked up, never blindly resent |
| Concurrency | SQLite process lock prevents two runners sharing one journal from submitting simultaneously |
| Portfolio accounting | Broker cash, positions and equity; expected quantities checked against tracked fills |
| Costs | Incremental configurable commissions, sell fees and extra slippage sensitivity; computed from cumulative actual paper fills |

**Free IEX is one exchange, not a consolidated market feed.** Alpaca's paper fills can use NBBO while your strategy/limits use IEX. This mismatch is disclosed; the system does not silently switch feeds. SIP access improves data coverage but does not make simulated fills realistic.

## What “accurate” means here

This is an auditable forward-testing system, not a claim to reproduce all live-market conditions. Alpaca paper trading does not realistically model available liquidity, order queue priority, market impact or latency slippage. The runner cannot fix those broker simulation assumptions. Use liquid ETFs and modest sizes, and inspect fill behavior.

Alpaca paper trading omits dividends. Consequently reports **are not total-return results**. Signal bars are split-adjusted, not dividend-adjusted. Unexpected position changes (including splits or manual trades) stop new trading pending investigation; automatic corporate-action accounting is not implemented. Taxes, borrowing costs and cash-account settlement restrictions are not modeled. No options, shorting, leverage or extended-hours strategies are supported. Cash-based sizing avoids intentional margin borrowing but does not constitute a T+1 settled-cash simulation; Alpaca paper account rules apply.

The cost fields default to zero fees and **5 basis points of additional slippage per filled notional**. These are scenario assumptions, not a verified broker fee schedule. Configure them for the intended live account. Only add costs omitted from broker equity; do not charge the spread twice when it is already in fill prices. Estimated costs affect reported adjusted P&L, not the broker's cash ledger. Commissions are reserved when sizing orders; other estimated costs do not reduce future strategy capital.

The JSON/HTML report shows account equity from the latest reconciliation snapshot, additional cost estimates, orders, and limitations. A fill received later in the cycle appears before its equity impact is captured; the next cycle reconciles the account. Do not use the example's profitability as evidence of an edge. Historical research and genuinely unseen forward results remain separate tasks.

## Failure handling

- A lost response after submission leaves an `attempted` order. The next cycle looks it up by its client ID and resumes only if it can establish the outcome.
- An unknown submission stops trading. Inspect the paper dashboard and journal; the system deliberately provides no blind retry button. If you cannot establish the outcome, stop the run, cancel any paper orders, and start a new experiment with a fresh empty paper account/state.
- A position mismatch can be a fill race; a later reconciliation may resolve it. Persistent mismatches require checking broker activity/corporate actions.
- API authentication, entitlement, rate-limit and network errors are recorded in `events`. `run` retries the cycle at the polling interval; `once` exits with an error.
- State is bound to one account and one configuration. Preserve the SQLite database to resume; deleting it loses order provenance.

Reports and SQLite databases are private local artifacts excluded by `.gitignore`. Credentials are read only from environment variables and are not included in reports.

## Tests

```powershell
python -m unittest discover -s tests -v
```

Tests use a synthetic broker; authenticated Alpaca end-to-end execution requires your credentials and has not been verified merely by passing these tests.

## API references

- [Alpaca paper assumptions](https://docs.alpaca.markets/us/docs/paper-trading)
- [Order lifecycle and session eligibility](https://docs.alpaca.markets/us/docs/orders-at-alpaca)
- [Market calendar](https://alpaca.markets/sdks/python/api_reference/trading/calendar.html)
- [Historical bars, feed selection and adjustments](https://docs.alpaca.markets/us/reference/stockbars)

No GitHub repository was reused and no remote repository has been changed.
