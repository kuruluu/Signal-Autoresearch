CURRENT STATUS2026-11-26: ACTIVEunderusergoal. Supersedespriorpauseheaders.10000USD;allinstruments;DD50/DD30/DD20;papertradesauthorized;noliveorders;sealed2024-2025untouched. Commitnotableprogressincludingfailures tokuruluu/Signal-Autoresearchonceaccesspermits. P40soleactive;P117queued.

LATEST USER STATUS: PAUSED. This supersedes earlier resume statements. P40 methods/data reaudit is pending; no orders placed. Resume only on explicit user instruction.

RESUME UPDATE2026-11-25: Useractivatedupdatedgoal. AutonomousresearchactiveunderRESEARCH_MANDATE.json; earlierpausestatementsbelowarehistorical. P40issoleactivepaper;P117queued.

# Capital, drawdown and authorization amendment — 2026-11-25

RESEARCH_MANDATE.json governs prospective work: $10,000 initial capital, all instruments, and three separately reported drawdown tiers (50%, 30%, 20%). Default ranking is robust net CAGR subject to tier limits and registered evidence/benchmark gates. Estimate drawdown using equity paths and stress/resampling; historical compliance is not a future guarantee. Register overlays and data splits before results; control selection across strategies and tiers. Paper trades are authorized on the paper endpoint with $10,000 aggregate research budget; live trades remain unauthorized. Research remains paused. Access-related reaudits are in ALPACA_REVISIT_AUDIT.json. Frozen experiments retain their original rules.

# Scope amendment — 2026-11-25

The prospective objective is any reproducible executable market edge, not ETF-only or buy-and-hold. In the historical version-2 scheme below, read ETF transfer as any necessary instrument/market transfer. Skip transfer when the native strategy is already the intended executable instrument. Preserve all frozen protocols. Register the appropriate primary objective (incremental return, risk-adjusted return, or risk reduction) and controls before outcomes. Research is paused.

# Replication-first testing scheme — version 2

Effective 2026-11-22 for new research. This replaces the prospective workflow, not the historical results or frozen version-1 protocols. Subsequent registered partial reproduction and ETF bridge results are recorded in [CYCLE_RESULTS.txt](CYCLE_RESULTS.txt); these remain exploratory, with no independent confirmation.

## Stage-specific decisions

| Stage | Primary question | Comparison | Decision |
|---|---|---|---|
| Paper specification | What exact effect is claimed? | Source equations/table and data definitions | Ready or blocked |
| Reproduction | Can we recover that reported quantity? | Published estimate, uncertainty and implementation details | Reproduced, partial, inconsistent, inconclusive or blocked |
| ETF transfer | Does the mechanism appear in ETF data? | Same estimand with documented instrument/universe changes | Supported for further research, unsupported, inconclusive or blocked |
| Signal | Is a causal implementation economically useful? | Registered no-signal and exposure/risk controls after costs | Meets the registered economic objective, fails it, or inconclusive |
| Independent confirmation | Does a frozen implementation generalize? | Predeclared fresh-period decision rule | Confirmed under specified conditions, failed or inconclusive |

A paper may reproduce but fail ETF transfer. An effect may transfer but be too small to trade after costs. An adaptation can be profitable without reproducing its source paper. Record these outcomes separately.

## Reproduction specification

Complete `experiment_template.json` for one primary result, including the paper version and page/table/equation, estimand and units, original sample and universe, published estimate and uncertainty, timing, filters, transformations, portfolio weights/regression controls and standard-error method. Document author code and supplemental material access. Every unresolved methodological choice needs an explicit source or a labeled deviation.

Freeze numerical acceptance tolerances before calculating the result. For identical data/code, use a tolerance justified by rounding and numerical precision. With a documented data vintage difference, predefine an effect-size tolerance and a discrepancy assessment appropriate to dependence between estimates; overlapping confidence intervals alone do not establish equivalence. Do not choose tolerances to make results match. If published uncertainty is unavailable, record that and narrow the claim.

Reproduce the native horizon and original gross/net convention. A monthly excess-return regression cannot be validated by a five-day long-only backtest. Reproduce original inference first and report any corrected or dependence-aware analysis separately. Audit survivorship and retrospective normalization without silently changing the original specification. Distinguish reproducibility of a reported number from credibility of its economic interpretation or causal explanation.

## Transfer and signal construction

Use a registered sequence of bridge experiments. Where feasible, change only one major element per experiment: source instruments to ETFs, original holding horizon to intended horizon, long/short to long-only, weighting, then execution. Show the effect of each change and log unavoidable confounding changes. There is no requirement to obtain a 2–10-day signal if the effect only supports a longer horizon.

Information must be available at the decision timestamp, including lagged revisions/releases. An economic association does not automatically imply a forecast. Validate predictive timing and information leakage before interpreting a signal. Separate the effect estimator from the order/execution layer.

## Controls learned from earlier tests

Use a small factorial design where relevant: signal on/off crossed with scaling on/off, with the same schedule and costs. Report market beta, cash allocation, exposure, turnover, concentration and volatility. Include a comparator whose exposure/risk is matched using only past information, specifying the algorithm before evaluation. Report ex-post matching only as a diagnostic. Comparisons on realized volatility cannot be relabeled investable benchmarks.

Treat cash interest as part of portfolio return. Obtain a historical causal rate series when possible; otherwise show registered plausible cash-return scenarios and limit conclusions. Account for differences in leverage, borrowing and trading costs. Keep passive buy-and-hold as context; it need not be the primary comparator for every paper.

Choose exactly one primary economic objective before results:

- Incremental net return: specify the control and minimum economically meaningful annualized improvement.
- Risk-adjusted usefulness: specify the factor model or past-information risk target, primary statistic, estimation procedure and minimum improvement.
- Risk reduction: specify a risk measure, minimum improvement and an acceptable return sacrifice. Drawdown estimates require path-aware uncertainty, not a mean-return interval.

Report all outcomes and tradeoffs, but do not promote a secondary outcome after the primary test fails. The previous “positive raw active return in both short periods” gate remains a historical rule, not a universal replication standard. Replace it only prospectively with a justified, paper-specific criterion. Year/regime signs are diagnostics unless a mechanism-specific consistency requirement is registered.

## Statistical and Monte Carlo design

Before execution, define the null, alternative, estimand, primary endpoint, economically meaningful effect, inferential family, correction and confidence level. Use the default 5% familywise level only if justified; record any alternative before results. Correct across the actual searched claims, including primary objective/variant choices. Distinct estimands need compatible inference, not arbitrary concatenation into a return matrix. Holm adjustment can combine valid p-values across different tests; synchronized maximum-statistic bootstrap requires a defensible common resampling design. Neither method erases unrecorded adaptive research.

Match dependence handling to the original data: time clustering, cross-sectional clustering, overlapping-return HAC or block resampling as appropriate. Keep related assets/strategies synchronized. When labels or holdings overlap split boundaries, define purging and embargo from their information/holding windows; do not reuse the old ten-session gap automatically. If fitting/tuning, use nested chronological evaluation and fit/selection-aware resampling.

Specify bootstrap/Monte Carlo purpose, seed, replications, block lengths, sensitivity cases and assumptions. The former 2,000 paths can be an exploratory starting point, not an automatic adequacy guarantee. For estimated tail probabilities report Monte Carlo precision (for example binomial sampling error with the relevant finite-count correction) and predeclare an escalation rule near decision thresholds. Resampling fixed strategy returns is acceptable only for a fixed-rule return estimand; it does not validate a fitted pipeline or simulate unseen regimes.

Assess power or minimum detectable effects before interpreting non-rejection as no useful signal. Report magnitude and uncertainty even when significance fails. Execution simulations vary spreads, slippage, delays, missed/partial fills and capacity using observed evidence or clearly labeled assumptions. They complement, rather than replace, statistical inference and independent observations.

## Data boundaries and registrations

All history through 2023 is used development evidence for new choices. Exact reproduction of an old published result can use that history, but is not fresh confirmation. Final 2024–2025 stays sealed. Explicit release authorization, a separately frozen release protocol and a permanent consumption record are required before access. Do not fetch an unbounded dataset and then discard final-period rows: access has already occurred. Extend the consumed-data ledger to any additional source/sample inspected.

Use append-only trial records with stable IDs and stage/parent relationships. Include failed runs, altered specifications, abandoned variants and exploratory decisions. Keep original artifacts immutable; new scientific definitions get new directories and hashes. Literature candidates are not the unit of multiple testing. Maintain prior test history even when new statistical families differ.

## Implementation boundary

The current `engine.py` is a long-only daily ETF cohort simulator. Build paper-specific estimation modules as needed; do not force native monthly factor, long/short futures or intraday models through it. `experiment_template.json` is an incomplete design skeleton, not an executable registration. A future runner must refuse missing required fields, record source/code/data hashes before evaluation and maintain distinct replication, transfer and economic verdicts.

The current handoff is `HANDOFF.txt`, mirrored at the workspace root. Report generators preserve it instead of reinstating old prompts. Historical handoff context is archived in `PRE_REVISION_HANDOFF.txt`.


## Sequential execution amendment — 2026-11-22

Follow SEQUENTIAL_POLICY.txt and paper_queue.json. Keep one paper active through its method audit, reproduction, ETF transfer and economic evaluation as feasible. A failed registered criterion, unresolved uncertainty or documented missing-input blocker moves that paper aside; it does not imply the published effect is false or require stopping the entire queue. Do not retune failed specifications. Record the disposition and update the handoff before advancing. Stop the overall loop when there is no meaningful new progress and no concrete feasible next-paper action. Historical results and sealed-period rules remain unchanged.


## Methods safeguards learned from cycles 6-8

P65 uses different dependent-variable definitions in its descriptive and forecasting procedures. Audit these separately: future-data adjustments permitted for a faithfully labeled descriptive reproduction cannot enter an executable forecast. Register training windows, seasonal estimation and normalization timing explicitly. P37 studies liquidity and mispricing dynamics; do not treat liquidity Granger predictability or an impulse response as a net-return trading signal. Register identification/order sensitivity and require causal preprocessing for a forecast branch. Accessibility supplements containing published tables or figures do not substitute for underlying input observations.


P28 source-convention lesson (cycle103): distinguish the return convention in a paper from the convention of its downloadable workbook. A percentage cell format proves neither simple nor log returns. Verify units, excess versus total, and stock-versus-portfolio aggregation before numerical gates. When a documented method suggests one correction after mismatch, freeze it separately, preserve the first result, prohibit transform/endpoint searches, and label a match as inferred partial reconstruction until provenance is established. Matching published numbers does not create independent confirmation or executable performance.
