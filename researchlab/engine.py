"""Daily open-marked, nonoverlapping cohort accounting with explicit costs."""
from dataclasses import dataclass
import numpy as np
import pandas as pd


@dataclass
class Result:
    daily: pd.DataFrame
    trades: pd.DataFrame
    contribution: pd.DataFrame


def backtest(panel, raw, p, start, end, hold=5, cost_multiplier=1, delay=0,
             miss=0.0, subset=None, seed=6413):
    dates = panel['adj_open'].index
    op = panel['adj_open'].to_numpy()
    if not np.isfinite(op).all() or (op <= 0).any():
        raise ValueError('Invalid execution prices')
    weights = raw.reindex(index=dates, columns=panel['adj_open'].columns).to_numpy()
    if not np.isfinite(weights).all() or (weights < 0).any():
        raise ValueError('Only finite long-only weights supported')
    returns = panel['adj_close'].pct_change(fill_method=None).to_numpy()
    adv = panel['dollar_volume'].rolling(20).mean().to_numpy()
    valid = np.flatnonzero((dates >= start) & (dates <= end))
    if len(valid) < hold + 2:
        raise ValueError('Insufficient evaluation period')
    first, last = valid[0], valid[-1]
    symbols = list(panel['adj_open'].columns)
    mask = np.array([subset is None or s in subset for s in symbols])
    cost = sum(p['cost_bps_per_side'].values()) / 10000 * cost_multiplier
    rng = np.random.default_rng(seed)
    n = len(symbols)
    units, gross_units = np.zeros(n), np.zeros(n)
    cash = gross_cash = previous = previous_gross = float(p['capital'])
    entry = None
    trades, daily, contributions = [], [], []
    next_entry = first + delay
    exit_at = None
    for t in range(first, last + 1):
        before = cash + units @ op[t]
        gross_before = gross_cash + gross_units @ op[t]
        contribution = units * (op[t] - op[t - 1]) / previous if t > first else np.zeros(n)
        turnover = 0.0
        if exit_at == t:
            values = units * op[t]
            cash += values.sum() * (1 - cost)
            gross_cash += gross_units @ op[t]
            turnover += values.sum() / before
            for k in np.flatnonzero(units):
                proceeds = values[k] * (1 - cost)
                invested = entry['values'][k] * (1 + cost)
                trades.append({'symbol': symbols[k], 'entry': str(dates[entry['t']].date()),
                               'exit': str(dates[t].date()), 'sessions': t - entry['t'],
                               'net_pnl': proceeds - invested, 'net_return': proceeds / invested - 1,
                               'notional': entry['values'][k], 'cohort': entry['t']})
            units[:] = 0
            gross_units[:] = 0
            exit_at = None
        if t == next_entry and t + hold <= last:
            signal_t = t - 1 - delay
            if signal_t < p['risk_lookback']:
                raise ValueError('Insufficient pre-signal risk history')
            w = weights[signal_t].copy()
            w[~mask] = 0
            w[adv[signal_t] < p['liquidity_min_trailing_dollar_volume']] = 0
            cov = np.cov(returns[signal_t - p['risk_lookback'] + 1:signal_t + 1], rowvar=False)
            risk = float(np.sqrt(max(0, w @ cov @ w) * 252))
            if risk > 0:
                w *= min(1, p['risk_target_annual'] / risk)
            w = np.minimum(w, p['per_asset_cap'])
            if w.sum() > p['gross_cap']:
                w *= p['gross_cap'] / w.sum()
            w = np.minimum(w, adv[signal_t] * p['max_trade_participation_trailing_volume'] / max(cash, 1))
            w[rng.random(n) < miss] = 0
            values = cash * w / (1 + cost)
            gross_values = gross_cash * w
            units = values / op[t]
            gross_units = gross_values / op[t]
            cash -= values.sum() * (1 + cost)
            gross_cash -= gross_values.sum()
            turnover += values.sum() / before
            entry = {'t': t, 'values': values.copy()}
            exit_at = t + hold
        if t == next_entry:
            next_entry += hold
        equity = cash + units @ op[t]
        gross_equity = gross_cash + gross_units @ op[t]
        if cash < -1e-6 or equity <= 0:
            raise ValueError('Invalid cash/equity')
        daily.append({'date': dates[t], 'net_return': equity / previous - 1,
                      'gross_return': gross_equity / previous_gross - 1, 'equity': equity,
                      'exposure': units @ op[t] / equity, 'turnover': turnover,
                      'cash': cash, 'cost_return': max(0, before - equity) / previous})
        contributions.append(contribution)
        previous, previous_gross = equity, gross_equity
    if np.any(units):
        raise AssertionError('All cohorts must be closed within evaluation period')
    frame = pd.DataFrame(daily).set_index('date')
    return Result(frame, pd.DataFrame(trades), pd.DataFrame(contributions, index=frame.index, columns=symbols))


def passive(panel, start, end, symbols=None):
    prices = panel['adj_open'].loc[start:end]
    if symbols:
        prices = prices[symbols]
    # 90% initial equal allocations, buy-and-hold drift; 5 bps at entry and exit.
    wealth = .1 + .9 / 1.0005 * (prices / prices.iloc[0]).mean(axis=1)
    wealth.iloc[-1] -= (.9 / 1.0005 * (prices.iloc[-1] / prices.iloc[0]).mean()) * .0005
    r = wealth.pct_change(fill_method=None)
    r.iloc[0] = wealth.iloc[0] - 1
    return r


def metrics(result, benchmark):
    d = result.daily
    r = d.net_return
    t = result.trades
    wealth = np.r_[1., np.cumprod(1 + r)]
    total = wealth[-1] - 1
    vol = r.std(ddof=1) * np.sqrt(252)
    active = r - benchmark.reindex(r.index)
    beta = np.cov(r, benchmark)[0, 1] / max(np.var(benchmark, ddof=1), 1e-16)
    return {'net_total_return': total, 'gross_total_return': np.prod(1 + d.gross_return) - 1,
            'net_cagr': wealth[-1] ** (252 / len(r)) - 1, 'volatility': vol,
            'sharpe_zero_cash_rate': r.mean() * 252 / vol if vol > 0 else None,
            'max_drawdown': float(np.min(wealth / np.maximum.accumulate(wealth) - 1)),
            'annual_one_way_turnover': d.turnover.mean() * 252,
            'mean_exposure': d.exposure.mean(), 'time_invested_fraction': (d.exposure > 0).mean(),
            'round_trips': len(t), 'order_sides': 2 * len(t), 'nonoverlapping_cohorts': int(t.cohort.nunique()) if len(t) else 0,
            'mean_holding_sessions': t.sessions.mean() if len(t) else None,
            'trade_win_rate': (t.net_pnl > 0).mean() if len(t) else None,
            'average_winning_trade_return': t.loc[t.net_return > 0, 'net_return'].mean() if len(t) else None,
            'average_losing_trade_return': t.loc[t.net_return <= 0, 'net_return'].mean() if len(t) else None,
            'benchmark_total_return': np.prod(1 + benchmark) - 1,
            'active_mean_annualized': active.mean() * 252, 'benchmark_beta': beta,
            'alpha_linear_annualized': (r.mean() - beta * benchmark.mean()) * 252,
            'daily_observations': len(r), 'effective_independent_sample_size': 'not assumed; dependent bootstrap used',
            'max_single_trade_abs_pnl_share': float(t.net_pnl.abs().max() / t.net_pnl.abs().sum()) if len(t) and t.net_pnl.abs().sum() else None}
