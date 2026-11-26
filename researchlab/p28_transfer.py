"""P28 ETF transfer, fixed prior-only beta control; not account simulation."""
from pathlib import Path
import json,hashlib
import numpy as np
import pandas as pd
from .reality_check import stationary_indices
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'research/replication_first';OUT=BASE/'p28_transfer_001';INPUT=BASE/'p28_transfer_inputs'

def control(returns):
    result=[]
    for i in range(36,len(returns)):
        past=returns.iloc[i-36:i].to_numpy();beta=np.cov(past.T,ddof=1)[0,1]/np.var(past[:,1],ddof=1)
        beta=float(np.clip(beta,0,1));result.append([returns.iloc[i,0],beta*returns.iloc[i,1],returns.iloc[i,1],beta])
    return pd.DataFrame(result,index=returns.index[36:],columns=['SPLV','control','SPY','beta'])

def metrics(a):
    sr=a.mean(axis=-2)/a.std(axis=-2,ddof=1)*np.sqrt(12)
    return (a[...,0]-a[...,1]).mean(axis=-1)*12,sr[...,0]-sr[...,1]

def freeze():
    files=[Path(__file__),ROOT/'researchlab/reality_check.py',OUT/'registration.json',INPUT/'SPLV.csv',INPUT/'SPY.csv']
    with (OUT/'analysis_freeze.json').open('x') as f:json.dump({'hashes':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}},f,indent=2)

def main():
    s=json.loads((OUT/'analysis_freeze.json').read_text())
    for p,h in s['hashes'].items():
        if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise ValueError('Frozenfilechanged')
    if (OUT/'results.json').exists():raise ValueError('Alreadyevaluated')
    series=[];dates=None
    for symbol in ['SPLV','SPY']:
        f=pd.read_csv(INPUT/(symbol+'.csv'),index_col='date',parse_dates=True)
        if dates is not None and not dates.equals(f.index):raise ValueError('Dailyalignment')
        dates=f.index
        if f.isna().any().any() or not (f>0).all().all() or f.index.max()>=pd.Timestamp('2024-01-01'):raise ValueError('Invalidprices')
        monthly=f.adj_close.groupby(f.index.to_period('M')).last()
        if not monthly.index.equals(pd.period_range('2011-05','2023-12',freq='M')):raise ValueError('Missingmonths')
        series.append(monthly.pct_change(fill_method=None).iloc[1:])
    returns=pd.concat(series,axis=1);returns.columns=['SPLV','SPY'];panel=control(returns)
    if not panel.index.equals(pd.period_range('2014-06','2023-12',freq='M')):raise ValueError('Scoringcoverage')
    a=panel[['SPLV','control']].to_numpy();mean,gap=metrics(a);intervals=[]
    for block in (3,12,24):
        idx=stationary_indices(len(a),10000,1/block,np.random.default_rng(281000+block));m,g=metrics(a[idx])
        intervals.append({'block_months':block,'paths':10000,'seed':281000+block,'annual_mean_advantage_ci95':np.quantile(m,[.025,.975]).tolist(),'sharpe_advantage_ci95':np.quantile(g,[.025,.975]).tolist()})
    result={'type':'DistinctlowvolETFmechanismtransfer','months':len(a),'first':str(panel.index[0]),'last':str(panel.index[-1]),'annual_mean_advantage':float(mean),'sharpe_advantage':float(gap),'annual_arithmetic_means':(panel[['SPLV','control','SPY']].mean()*12).to_dict(),'annual_sharpes':(panel[['SPLV','control','SPY']].mean()/panel[['SPLV','control','SPY']].std(ddof=1)*np.sqrt(12)).to_dict(),'beta_min_max':[float(panel.beta.min()),float(panel.beta.max())],'bootstrap':intervals,'gate_pass':bool(mean>0 and gap>0 and all(x['annual_mean_advantage_ci95'][0]>0 and x['sharpe_advantage_ci95'][0]>0 for x in intervals)),'strategy_validated':False,'independent_confirmation':False}
    with (OUT/'results.json').open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps(result,indent=2))
if __name__=='__main__':
    import sys
    freeze() if '--freeze' in sys.argv else main()
