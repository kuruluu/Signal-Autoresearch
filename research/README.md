# ETF signal research platform

**Current direction:** [Replication-first testing scheme](replication_first/TESTING_SCHEME.md). New work first reproduces a precisely specified paper effect, then tests ETF transfer and economic usefulness separately. [Current handoff](replication_first/HANDOFF.txt) supersedes earlier next-step prompts. Existing run commands and frozen protocols below still reproduce the historical experiments; they do not execute the new scheme.

The latest continuation adds **50 candidates and a registered trend-control experiment**. See [continuation report](expansion_001/report.html) and [continuation methods and commands](expansion_001/README.md). The original study described below is preserved.

Open **dashboard.html** in a browser. The dashboard runs locally without a server, credentials or third-party JavaScript. Source links, paper records, CSV/JSON exports, variant filters and base equity curves are included. It is a research report, not a brokerage dashboard.

## What was done

The original `paperlab` modules were inspected and preserved. Their current-market broker fills are not suitable for historical inference, so `researchlab` is an independent module with **no brokerage order access**. It uses the existing project's Python workflow but separate data, signals, accounting and reports.

The platform resolves 50 distinct papers to canonical metadata, records lawful full-text retrieval attempts, and assesses every paper's feasibility. A paper's accessible public working copy may differ from its published version. Bibliographic verification and a targeted methods review are not a complete replication audit. Unknown original sample dates are explicitly unknown. Inaccessible data and methods are blockers, not invitations to invent them.

21 ETF hypotheses linked to 24 papers were implemented. Multiple related papers can map to one hypothesis; they are not independent successful experiments. The other 26 papers are data/method-blocked or methodological references. No original-paper replication is claimed.

## Commands

From the workspace root on this computer:

```powershell
.\research.ps1 test
.\research.ps1 catalog
.\research.ps1 sources
.\research.ps1 review
.\research.ps1 data
.\research.ps1 pilot
.\research.ps1 run
.\research.ps1 report
```

These commands respectively test, verify bibliography, retrieve available public PDFs, generate review records, cache/validate observations, run the three-hypothesis pilot, evaluate the full variant family, and build the dashboard/handoff. Network commands use cached responses where possible. Access errors are recorded, not treated as successful retrievals. Public-provider access and availability can change.

For another machine, install Python 3.11+ and the research extra:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e '.[research]'
.\.venv\Scripts\python -m researchlab.catalog
.\.venv\Scripts\python -m researchlab.sources
.\.venv\Scripts\python -m researchlab.review
.\.venv\Scripts\python -m researchlab.data
.\.venv\Scripts\python -m researchlab.experiment --pilot
.\.venv\Scripts\python -m researchlab.experiment
.\.venv\Scripts\python -m researchlab.report
```

Local auxiliary dependencies are in `.research-deps`, excluded from Git. Package versions and code hashes used for a run are recorded in registration files. Do not remove existing data or result directories to conceal failed experiments. The failed initial pilot is preserved in `pilot_failed_001`; its regime-report mask bug was fixed before the successful pilot/full run.

## Study design

`protocol.json` was written before performance testing. It defines the universe, split boundaries, assumptions and success gates. `results/registration.json` freezes the signal definitions, all 11 variants and computational code hashes before that run. Changed computational code/protocol is refused on rerun against an existing registration. Preserve the original artifacts and create a new versioned experiment for changes; do not bypass the guard by deleting registration files.

The 12 ETFs were selected for asset-class coverage, not backtested performance. They are nevertheless a **fixed surviving universe**, not a point-in-time fund-selection sample. The platform cannot infer ETF-population profitability or eliminate survivorship bias from these observations.

- 2007-2009 provides warmup. 2010-2016 is available for retrospective development/own-sample tests.
- Validation nominally spans 2017-2020. The shared comparison begins in 2019, after all implemented source publications; this is deliberately conservative relative to earlier working papers.
- Walk-forward evaluation uses 2021-2023. Rules are fixed; rolling covariance uses only historical observations. This is chronological fixed-rule execution, not repeatedly refitted predictive machine learning.
- Each evaluation begins after a ten-session boundary gap. Cohorts close within the split. There are no fitted forward-return labels crossing boundaries; no overlapping trade cohorts are treated as independent.
- 2024-2025 is sealed: normal commands neither download nor evaluate those daily bars. `observed_periods.json` records all examined history. A future release requires a newly frozen protocol and permanent consumption record. This is a workflow guard, not a security boundary against someone deliberately editing the code.

Original-paper dates and methodology can differ. The ETF adaptations are not representations of what an investor actually knew across all historical vendor revisions. Post-publication available-sample results and common-sample results are separate files.

## Data

Data comes from Yahoo's public chart endpoint, not Alpaca IEX. Raw payloads include distributions and splits. `data/manifest.json` records URLs, cache timestamps, row counts and checksums. Public adjusted history is revised and cannot be represented as point-in-time data. Cache timestamps reflect the local execution host clock.

All assets were checked against `exchange_calendars` XNYS sessions. The saved exchange schedule handles weekends, holidays, exceptional closures, early closes and DST. Daily open executions do not require an invented intraday close timestamp. Missing/non-finite observations, duplicate dates, inconsistent OHLC and calendar mismatches stop processing; no implicit forward filling.

The engine uses `adjusted_open = open * adjusted_close / close`, approximating reinvested distributions in synthetic fractional units. This is a total-return approximation, **not** a complete historical share, cash, dividend and settlement ledger. Fees already embedded in fund returns are not added again. The data does not supply historical bid/ask spreads, auction order books, delisted ETF selection or borrow costs.

## Execution and portfolios

Signals use the previous completed close. Positions enter at the next session's adjusted open benchmark, with explicit modeled transaction costs. Primary holdings last five sessions; sensitivity runs use two and ten. Each nonoverlapping cohort is fully closed before opening the next, even if it selects the same assets. This deliberately charges a complete round trip and is more costly than netting unchanged positions.

Portfolios are long-only and unleveraged. Entry weights have a 90% gross cap, a 20% per-asset cap and an ex-ante 10% annual risk ceiling based on trailing 60-session covariance. These are formation constraints; exposure can drift during a cohort and realized risk can exceed the estimate. A trailing $10m daily-dollar-volume floor and 0.1% trade-participation cap apply. Fractional adjusted units are research accounting, not brokerage lot sizes.

Base costs are **assumed**: 0 commission + 2bps half-spread + 3bps slippage per side. Each fill reduces capital; 2x/4x stress scales all these components. Delayed-entry, 10% missed-trade, 80%/120% lookback, equities-only and defensive-only variants are retained. The miss process is a seeded stress model, not an estimate of real fill probabilities. Daily opens are reference prices, not guaranteed executions. Cash earns zero, creating a material limitation for cash-heavy strategies. No intraday fill precision, taxes, financing, options, shorting, margin or settled-cash simulation is asserted.

The primary benchmark starts 90% invested equally across the same ETFs and holds through the period. SPY and cash comparisons are also saved. Benchmarks incur entry/exit costs. Strategies generally carry different exposures; raw active returns do not establish pure signal alpha. Linear beta/alpha, exposure, volatility and concentration diagnostics help identify that difference but do not replace a full factor model. An exposure-matched benchmark is a documented follow-up, not a silently substituted primary benchmark.

## Statistics

Each strategy has 11 registered variants: 231 experiments and 462 split evaluations. The pilot used three representative hypotheses: own-return trend, weekly reversal and inverse-variance allocation. Gross/net returns, CAGR, Sharpe with zero cash rate, volatility, maximum drawdown, turnover, exposure, time invested, holding duration, per-asset round trips, cohort counts, win/loss statistics, linear benchmark beta/alpha and concentration are saved. Sharpe is not accompanied by a false independent-daily-observation significance claim.

The stationary bootstrap draws 2,000 paths at each of mean block lengths10,20,40, with shared resampling indices for every strategy. This preserves contemporaneous dependence and local serial dependence. It resamples fixed strategies' daily active returns, not refitted models or order-book paths. It cannot create absent regimes. Intervals concern the mean daily active return; annualized presentation multiplies the mean, not the sampling frequency.

For the null, active returns are centered and studentized using bootstrap standard errors. The maximum statistic across **all231variants** provides a familywise comparison; a conservative50-paper Bonferroni floor is also applied. This controls the registered finite family under the bootstrap assumptions, not unknown prior researcher searches. The finite simulation count limits p-value resolution. Subperiod/year, past-information market regimes, asset subsets, correlations and trade/asset concentration are additional diagnostics, not independent confirmations.

No model parameters are fitted to maximize test performance. If future research adds fitting or model selection, it must add nested chronological validation and a refit/selection-aware uncertainty procedure; the current fixed-strategy bootstrap is insufficient for that purpose.

## Interpretation

`results/success_assessment.json` applies the predeclared gates. A provisional candidate must pass both evaluation periods, dependence-aware intervals, multiple testing, higher costs and year-to-year consistency. Even a provisional candidate would not be a robust success without the original-input/universe audit and final untouched evaluation.

No base hypothesis passed all gates in this run. Do not describe the highest return as a discovered edge. No conclusion here refutes the original papers: the instrument, horizon, long/short construction and execution may be materially different.

`../SIGNAL_SIMILARITIES.txt` explicitly separates observed correlations and common inputs from claims about successful signals. `../SIGNAL_RESEARCH_HANDOFF.txt` contains the project state, commands, blockers, failed gates, evidence paths, consumed periods and a reusable follow-up prompt.

## Evidence map

- `papers.json`, `papers.csv`, `paper_records/Pxx.txt`: bibliography, review depth, original data/horizon, findings, adaptations and blockers.
- `sources/`: raw Crossref and selected web evidence. Duplicate versions are counted once in the canonical catalog.
- `fulltext_access.json`, `fulltext/`: source-access attempts and successfully retrieved public copies. Respect original copyrights; these are private research inputs, not a redistribution bundle.
- `results/metrics.json`: all metrics and block-length uncertainty results.
- `results/*_daily.csv`, `*_trades.csv`, `*_contributions.csv`: base-case audit trails.
- `results/*_active_all_variants.csv`: synchronized active returns for all variants.
- `results/*_own_sample.json`: each signal's post-publication available sample.
- `results/*_regimes.json`, `asset_concentration.json`, `*_active_correlation.csv`: robustness diagnostics.

No paid service was used and no trades were submitted.
