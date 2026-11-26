"""Registered working-paper reproduction; never an independent investment test."""
import argparse
import hashlib
import io
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / 'research/replication_first/p52_audit'
OUT = ROOT / 'research/replication_first/p52_partial_001'
COLS = ['Lo 20', 'Qnt 2', 'Qnt 3', 'Qnt 4', 'Hi 20']
PUBLISHED = np.array([[1.93, 1.50], [1.63, 1.23], [1.45, 1.22], [1.30, 1.10], [.80, .72]])


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def daily_table(path, marker=None):
    lines = Path(path).read_text(encoding='utf-8-sig').splitlines()
    start = next(i for i, s in enumerate(lines) if marker in s) + 1 if marker else 0
    header = next(i for i in range(start, len(lines)) if lines[i].startswith(','))
    end = header + 1
    while end < len(lines) and re.match(r'^\s*\d{8},', lines[end]):
        end += 1
    frame = pd.read_csv(io.StringIO('\n'.join(lines[header:end])), index_col=0)
    frame.columns = frame.columns.str.strip()
    frame.index = pd.to_datetime(frame.index.astype(str), format='%Y%m%d')
    if not frame.index.is_unique or not frame.index.is_monotonic_increasing:
        raise ValueError('Duplicate or unordered dates')
    if frame.index.max() >= pd.Timestamp('2024-01-01'):
        raise ValueError('Sealed observations forbidden')
    return frame.replace([-99.99, -999], np.nan).astype(float) / 100


def signals(returns, window=50):
    levels = (1 + returns).cumprod()
    average = levels.rolling(window).mean()
    ma = levels.gt(average)
    momentum = levels.gt(levels.shift(window))
    valid = average.notna() & levels.shift(window).notna()
    return ma.where(valid), momentum.where(valid), levels, average


def strategy_returns(returns, rf, position):
    # Closing information at t controls the t+1 close-to-close return.
    prior = position.shift(1)
    return returns.mul(prior).add(prior.rsub(1).mul(rf, axis=0)).astype(float)


def holm(p):
    order = np.argsort(p)
    result = np.empty(len(p))
    result[order] = np.minimum(1, np.maximum.accumulate(np.array(p)[order] * np.arange(len(p), 0, -1)))
    return result


def bootstrap(values, block, paths=5000, seed=52001):
    values = np.asarray(values, dtype=float)
    n, k = values.shape
    rng = np.random.default_rng(seed + block)
    means = np.empty((paths, k))
    for offset in range(0, paths, 100):
        count = min(100, paths-offset)
        indices = np.empty((count, n), dtype=int)
        indices[:, 0] = rng.integers(n, size=count)
        for j in range(1, n):
            restart = rng.random(count) < 1 / block
            indices[:, j] = np.where(restart, rng.integers(n, size=count), (indices[:, j-1]+1) % n)
        means[offset:offset+count] = values[indices].mean(axis=1)
    observed = values.mean(axis=0)
    p = (1 + (np.abs(means-observed) >= np.abs(observed)).sum(axis=0)) / (paths+1)
    return dict(block_months=block, paths=paths, mean_difference_monthly_pp=(100*observed).tolist(),
                percentile_95_monthly_pp=(100*np.quantile(means, [.025, .975], axis=0).T).tolist(),
                centered_two_sided_p=p.tolist(), holm_p=holm(p).tolist(),
                approximate_p_mc_se=np.sqrt(p*(1-p)/(paths+1)).tolist())


def register():
    files = ['Portfolios_Formed_on_ME_daily.CSV', 'F-F_Research_Data_Factors_daily.CSV', 'working_paper_2014.pdf']
    spec = dict(experiment_id='P52_partial_001', stage='working_paper_partial_reproduction',
        target='December 22 2014 manuscript, page 30 Table 1 Panel B, 50-session row',
        published_monthly_mean_pct=PUBLISHED.tolist(), primary='Q1 MA minus TSMOM monthly mean, reported 0.43 percentage points',
        date_range=['1963-01-01', '2013-12-31'], warmup_start='1962-01-01', expected_months=612,
        universe=COLS, window=50, levels='Cumulative total-return index, including dividends; price-vs-total-return ambiguity disclosed',
        signal='Close > current-inclusive 50-observation SMA or close > close 50 observations ago; equality earns cash',
        timing='One-session shift; gross close-to-close reproduction, not executable close fills',
        cash='Contemporaneous French daily RF as realized cash return, never a signal input',
        aggregation='Compound daily gross returns within calendar month; arithmetic mean across full months',
        deviations=['August 2020 CRSP vintage from third-party snapshot, not original author inputs',
                    'Working paper not final 2017 article', 'Year endpoints interpreted as full calendar years; pre-1963 warmup',
                    'Total-return levels and equality-to-cash explicit assumptions',
                    'Original mean-difference inference insufficiently specified; bootstrap is supplemental, not original inference reproduction'],
        numerical_check=dict(each_mean_tolerance_pp=.15, primary_difference_tolerance_pp=.10,
            reason='Prospective approximate-match screen allowing vintage/definition discrepancy, not formal equivalence',
            partial_rule='All ten means within tolerance and Q1 difference positive and within tolerance; otherwise numerical inconsistency under this implementation'),
        uncertainty=dict(method='Joint stationary calendar-month bootstrap of fixed-rule paired differences',
            blocks=[6,12,24], paths=5000, seed=52001, correction='Holm across five quintile contrasts separately per block; all block choices reported',
            escalation='20000 paths with same seed if any primary adjusted p falls in [0.04,0.06]',
            scope='Conditional on fixed strategy histories; does not undo prior research selection or establish independent investment evidence'),
        data_hashes={str(INPUT / f):digest(INPUT / f) for f in files}, code_hash=digest(__file__),
        no_heldout_access=True, costs='None in gross reproduction; economic implementation must be separately registered')
    OUT.mkdir(exist_ok=True)
    file = OUT / 'registration.json'
    if file.exists():
        previous = json.loads(file.read_text())
        assert {k:v for k,v in previous.items() if k != 'registered_at_utc'} == spec, 'Frozen specification/code changed'
        return previous
    spec['registered_at_utc'] = datetime.now(timezone.utc).isoformat()
    file.write_text(json.dumps(spec, indent=2))
    return spec


def run():
    if not (OUT / 'registration.json').exists():
        raise ValueError('Register in a separate invocation before evaluation')
    spec = register()
    if (OUT / 'results.json').exists():
        raise ValueError('Completed experiment is immutable; read its existing results')
    returns = daily_table(INPUT / 'Portfolios_Formed_on_ME_daily.CSV', 'Value Weighted Returns -- Daily')[COLS].loc['1962':'2013']
    rf = daily_table(INPUT / 'F-F_Research_Data_Factors_daily.CSV')['RF'].reindex(returns.index)
    assert not returns.isna().any().any() and not rf.isna().any()
    ma, mom, levels, average = signals(returns)
    identity_error = float((50*average.diff()-(levels-levels.shift(50))).abs().max().max())
    ma_daily = strategy_returns(returns, rf, ma).loc['1963':'2013']
    mom_daily = strategy_returns(returns, rf, mom).loc['1963':'2013']
    assert not ma_daily.isna().any().any() and not mom_daily.isna().any().any()
    def monthly(frame):
        return (1+frame).groupby(frame.index.to_period('M')).prod()-1
    a, b = monthly(ma_daily), monthly(mom_daily)
    assert len(a) == spec['expected_months'] and a.index.equals(b.index)
    actual = np.column_stack([a.mean()*100, b.mean()*100])
    delta = a-b
    inference = [bootstrap(delta, block) for block in [6,12,24]]
    if any(.04 <= row['holm_p'][0] <= .06 for row in inference):
        inference = [bootstrap(delta, block, paths=20000) for block in [6,12,24]]
    checks = dict(all_means_close=bool((np.abs(actual-PUBLISHED)<=.15).all()),
                  primary_difference_close=bool(abs(float(delta.iloc[:,0].mean()*100)-.43)<=.10),
                  primary_difference_positive=bool(delta.iloc[:,0].mean()>0))
    result = dict(actual_monthly_mean_pct=actual.tolist(), published_monthly_mean_pct=PUBLISHED.tolist(),
        differences_from_published_pp=(actual-PUBLISHED).tolist(), checks=checks,
        verdict='Partial numerical reproduction' if all(checks.values()) else 'Numerically inconsistent under registered implementation',
        bootstrap=inference, months=len(a), first_month=str(a.index[0]), last_month=str(a.index[-1]),
        identity_max_abs_error=identity_error, eligible_signal=False,
        limitations=spec['deviations']+['No ETF transfer, transaction costs or independent evaluation in this experiment'])
    a.to_csv(OUT/'ma_monthly.csv'); b.to_csv(OUT/'tsmom_monthly.csv')
    (OUT/'results.json').write_text(json.dumps(result, indent=2))
    (OUT/'completion.json').write_text(json.dumps(dict(completed_at_utc=datetime.now(timezone.utc).isoformat(),
        hashes={x.name:digest(x) for x in OUT.iterdir() if x.is_file()}), indent=2))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    if args.run: run()
    else: register(); print('Registered P52_partial_001; no outcomes computed.')
