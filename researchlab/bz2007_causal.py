"""Registered prior-only quarterly forecasting test, not a trading backtest."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
from .bz2007_reproduction import ROOT, BASE, INPUT, digest
from .reality_check import stationary_indices

OUT = BASE/'bz2007_causal_001'


def load_panel():
    prices = pd.DataFrame(json.loads((INPUT/'spx_1989_2008.json').read_text()))
    dates = pd.to_datetime(prices.pop('date'))
    prices.index = pd.PeriodIndex(dates, freq='Q')
    grid = pd.period_range('1989Q4', '2008Q4', freq='Q')
    close = prices.close.groupby(level=0).last().reindex(grid)
    variance = pd.read_csv(INPUT/'related_variances.csv')
    variance.index = pd.PeriodIndex(variance.pop('month'), freq='M').asfreq('Q')
    x = variance.iv_minus_rv.groupby(level=0).last().reindex(grid).shift(1)
    bill = pd.read_csv(INPUT/'TB3MS_1989_2008.csv')
    bill.index = pd.PeriodIndex(bill.iloc[:, 0], freq='M').asfreq('Q')
    rf = bill.TB3MS.groupby(level=0).last().reindex(grid).shift(1)
    data = pd.DataFrame({'y': 400*np.log(close/close.shift(1))-rf, 'x': x})
    data = data.loc['1990Q2':]
    assert len(data)==75 and np.isfinite(data.to_numpy()).all()
    return data


def forecasts(data, start='2000Q1'):
    rows = []
    for i, quarter in enumerate(data.index):
        if quarter < pd.Period(start, freq='Q'):
            continue
        prior = data.iloc[:i]
        assert len(prior)>=39
        x = np.column_stack([np.ones(len(prior)), prior.x])
        beta, _, rank, _ = np.linalg.lstsq(x, prior.y, rcond=None)
        mean = float(prior.y.mean())
        valid = rank==2 and np.isfinite(beta).all()
        pred = float(beta@[1, data.x.iloc[i]]) if valid else mean
        rows.append({'quarter': str(quarter), 'actual': float(data.y.iloc[i]),
                     'forecast': pred, 'historical_mean': mean, 'valid': bool(valid),
                     'training_n': len(prior), 'training_last': str(prior.index[-1])})
    return pd.DataFrame(rows)


def inference(loss_gain, paths=10000):
    """Paired stationary loss bootstrap conditional on realized learning path."""
    gain = np.asarray(loss_gain, float)
    observed = float(gain.mean())
    rows = []
    for block in (2,4,8):
        indices = stationary_indices(len(gain), paths, 1/block, np.random.default_rng(200700+block))
        draws = gain[indices].mean(axis=1)
        lower, upper = np.quantile(draws, [.025,.975])
        p = (1+np.count_nonzero(draws-observed>=observed))/(paths+1)
        rows.append({'mean_block_quarters': block, 'ci95': [float(lower), float(upper)],
                     'one_sided_centered_p': float(p)})
    return rows


def register():
    files = [Path(__file__), ROOT/'researchlab/reality_check.py',
             INPUT/'related_variances.csv', INPUT/'spx_1989_2008.json',
             INPUT/'TB3MS_1989_2008.csv', BASE/'bz2007_partial_001/results.json']
    spec = {
        'id': 'BZ2007_causal_001', 'registered_at': datetime.now(timezone.utc).isoformat(),
        'sample': 'Training initially1990Q2-1999Q4 N39; expanding quarterly OLS; evaluation2000Q1-2008Q4 N36',
        'predictor': 'Previous quarter-end official IV-RV; constant and slope fit only on earlier completed quarters; no clipping/tuning',
        'response': 'Same annualized SPX price log excess return and lagged monthly bill approximation as partial reproduction',
        'control': 'Expanding arithmetic mean of exactly the same earlier quarterly responses',
        'fallback': 'If rank/nonfinite fit invalid, use mean and score all quarters; require100%valid model coverage',
        'gate': 'All: coverage100%; modelMSE at least1% lower than historical-meanMSE; paired loss-gainCI lower>0 and centered one-sidedp<=.05 for every block2/4/8',
        'inference': '10000 paired stationary bootstrap paths for loss gains; seeds200702/200704/200708. Conditional on fitted forecast path, no refits inside resamples; not structural paperDGP MonteCarlo.',
        'secondary': 'Report2005Q2-2008Q4 N15 descriptive MSE only; no separate success claim',
        'limitations': ['Already observed development sample, not untouched holdout.',
                       'VIX pre2003 back-calculation and realized-variance publication availability unresolved; prior-only numerical test not executable real-time backtest.',
                       'Short36quarter evaluation, end2008, no current-market evidence.',
                       'No dividend correction, bill-conversion changes or sample search after outcomes.',
                       'Quarterly horizon differs from desired days-long ETF positions. Separate economic/execution test required.'],
        'files': {str(f.relative_to(ROOT)):digest(f) for f in files}}
    OUT.mkdir(exist_ok=True)
    with (OUT/'registration.json').open('x') as f: json.dump(spec,f,indent=2)


def run():
    spec = json.loads((OUT/'registration.json').read_text())
    for file, expected in spec['files'].items(): assert digest(ROOT/file)==expected,file
    frame = forecasts(load_panel())
    assert len(frame)==36
    model_loss = (frame.actual-frame.forecast)**2
    control_loss = (frame.actual-frame.historical_mean)**2
    gain = control_loss-model_loss
    boot = inference(gain)
    improvement = float(1-model_loss.mean()/control_loss.mean())
    later = frame.quarter>='2005Q2'
    result = {'n':len(frame),'coverage':float(frame.valid.mean()),
              'model_mse':float(model_loss.mean()),'historical_mean_mse':float(control_loss.mean()),
              'relative_mse_improvement':improvement,'bootstrap':boot,
              'later_period':{'n':int(later.sum()),'relative_mse_improvement':float(1-model_loss[later].mean()/control_loss[later].mean())},
              'passes_gate':bool(frame.valid.all() and improvement>=.01 and all(b['ci95'][0]>0 and b['one_sided_centered_p']<=.05 for b in boot)),
              'scope':'Prior-only numerical development forecast test; no executable signal validated.'}
    with (OUT/'results.json').open('x') as f: json.dump(result,f,indent=2)
    frame.assign(model_loss=model_loss,control_loss=control_loss).to_csv(OUT/'forecast_panel.csv',index=False)
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['register','run'])
    {'register':register,'run':run}[parser.parse_args().action]()
