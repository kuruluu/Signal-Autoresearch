"""Idealized Monday-avoidance hurdle, not an executable account backtest."""
from pathlib import Path
import json, hashlib, datetime
import numpy as np
import pandas as pd
from .reality_check import stationary_indices

R = Path(__file__).resolve().parents[1]
B = R / 'research/replication_first'
O = B / 'p125_avoidance_001'
D = B / 'p24_inputs/author_daily_2021.csv'

def incremental_log(equity, cash, monday):
    equity, cash, monday = np.asarray(equity), np.asarray(cash), np.asarray(monday)
    if not (equity.shape == cash.shape == monday.shape):
        raise ValueError('Misaligned observations')
    if not np.isfinite(equity).all() or not np.isfinite(cash).all() or (equity <= -1).any() or (cash <= -1).any():
        raise ValueError('Invalid returns')
    return np.where(monday, np.log1p(cash) - np.log1p(equity), 0.)

def register():
    O.mkdir(exist_ok=True)
    s = {'id': 'P125_avoidance_001', 'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
         'windows': {'original': ['1953-01','1977-12'], 'later': ['1980-04','2020-12']},
         'construction': 'Idealized previous-session-close to Monday-close equity exposure replaced by cash. Other sessions unchanged. Cash variants zero interest and supplied daily rf. No holiday-Tuesday avoidance. Perfect index closes, zero costs; rf is a theoretical credit, not broker entitlement.',
         'gate': 'All 3/12/24month stationary bootstrap 95percent lower bounds of annual log-growth advantage positive in both windows and both cash variants. 10000 paths, seed125200+100*window+block, paired variants. No timing/holiday/period search. Failure stops executable transfer; pass requires separate costs and project-wide confirmation.',
         'limits': 'Not native replication or ETF/account validation. Window already viewed; dependent follow-up. No rank/order. No sealed2024-2025.',
         'hashes': {str(p.relative_to(R)): hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),D,R/'researchlab/reality_check.py']}}
    with (O/'registration.json').open('x') as f: json.dump(s,f,indent=2)

def main():
    s=json.loads((O/'registration.json').read_text())
    for p,h in s['hashes'].items():
        if hashlib.sha256((R/p).read_bytes()).hexdigest()!=h: raise ValueError('Changed frozen input')
    f=pd.read_csv(D,parse_dates=['date']).set_index('date')
    if f.index.max().year!=2020: raise ValueError('Unexpected source dates')
    results={}
    for wi,(name,(start,end)) in enumerate(s['windows'].items()):
        z=f.loc[start:end].copy()
        monday=z.index.dayofweek==0
        values=np.column_stack([incremental_log(z.vwretd,np.zeros(len(z)),monday),incremental_log(z.vwretd,z.rf,monday)])
        months=pd.DataFrame(values,index=z.index).groupby(z.index.to_period('M')).sum()
        if not months.index.equals(pd.period_range(start,end,freq='M')): raise ValueError('Missing month')
        x=months.to_numpy(); intervals=[]
        for block in (3,12,24):
            seed=125200+100*wi+block
            idx=stationary_indices(len(x),10000,1/block,np.random.default_rng(seed))
            intervals.append({'block':block,'paths':10000,'seed':seed,'annual_log_advantage_ci95':np.quantile(x[idx].mean(1)*12,[.025,.975],axis=0).tolist()})
        results[name]={'months':len(x),'annual_log_advantage_zero_rf':(x.mean(0)*12).tolist(),'bootstrap':intervals,'gate':all(min(v['annual_log_advantage_ci95'][0])>0 for v in intervals)}
    r={'windows':results,'advance':all(v['gate'] for v in results.values()),'strategy_validated':False,'independent_confirmation':False}
    with (O/'results.json').open('x') as f: json.dump(r,f,indent=2)
    print(json.dumps(r,indent=2))

if __name__=='__main__':
    import sys
    register() if '--register' in sys.argv else main()
