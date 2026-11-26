"""Fixed causal overnight EWMA and next-quarter partial mechanism test."""
import re,json,hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from .reality_check import stationary_indices

ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'research/replication_first';OUT=BASE/'p118_partial_001'


def riskfree(path):
    rows=[]
    for line in path.read_text().splitlines():
        if re.match(r'^\s*\d{8},',line):
            fields=line.split(',');rows.append((pd.to_datetime(fields[0].strip(),format='%Y%m%d'),float(fields[4])/100))
    result=pd.Series(dict(rows)).sort_index()
    if len(result)!=len(rows):raise ValueError('Duplicate RF date')
    return result


def panel(prices,rf):
    if not prices.index.is_unique or not prices.index.is_monotonic_increasing:raise ValueError('Invalid price dates')
    if (prices[['open','close','adj_close']]<=0).any().any():raise ValueError('Invalid price')
    total=prices.adj_close.pct_change(fill_method=None)
    intra=prices.close/prices.open-1
    overnight=(1+total)/(1+intra)-1
    monthly=(1+overnight).groupby(prices.index.to_period('M')).prod()-1
    monthly=monthly.loc['1993-02':]
    expected=pd.period_range('1993-02',monthly.index[-1],freq='M')
    if not monthly.index.equals(expected):raise ValueError('Missing predictor month')
    value=0.;smoothed=[]
    for ret in monthly:value=(ret+120*value)/121;smoothed.append(value)
    signal=pd.Series(smoothed,index=monthly.index)
    signal=signal.groupby(signal.index.asfreq('Q')).last()
    rf=rf.reindex(prices.index)
    if rf.isna().any():raise ValueError('Missing RF on SPY session')
    quarter=prices.index.to_period('Q')
    target=(1+total).groupby(quarter).prod()-(1+rf).groupby(quarter).prod()
    # Index rows by target quarter; signal is from the prior completed quarter.
    signal.index=signal.index+1
    return pd.DataFrame({'signal':signal,'target':target}).loc['1993Q3':'2019Q4'].dropna()


def slope(x,y):
    x=x-x.mean(axis=-1,keepdims=True);y=y-y.mean(axis=-1,keepdims=True)
    return (x*y).sum(axis=-1)/(x*x).sum(axis=-1)


def expanding(frame,initial=40):
    x=frame.signal.to_numpy();y=frame.target.to_numpy();pred=[];base=[]
    for i in range(initial,len(frame)):
        b=slope(x[:i],y[:i]);pred.append(y[:i].mean()+b*(x[i]-x[:i].mean()));base.append(y[:i].mean())
    model=float(np.mean((y[initial:]-pred)**2));benchmark=float(np.mean((y[initial:]-base)**2))
    return {'n':len(pred),'model_mse':model,'mean_mse':benchmark,'mse_improvement':1-model/benchmark}


def main():
    spec=json.loads((OUT/'registration.json').read_text())
    for name,digest in spec['hashes'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest
    freeze=json.loads((OUT/'analysis_freeze.json').read_text());assert freeze['code_sha256']==hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    assert not (OUT/'results.json').exists()
    prices=pd.read_csv(BASE/'p118_audit/SPY_1993_2019.csv',index_col='date',parse_dates=True)
    assert prices.index.max()<pd.Timestamp('2020-01-01')
    frame=panel(prices,riskfree(BASE/'p52_audit/F-F_Research_Data_Factors_daily.CSV'))
    if len(frame)!=106:raise ValueError('Registered106targetquartersnotmet')
    x=frame.signal.to_numpy();y=frame.target.to_numpy();observed=float(slope(x,y));intervals=[]
    for block in (4,8,12):
        idx=stationary_indices(len(frame),10000,1/block,np.random.default_rng(118000+block))
        draws=slope(x[idx],y[idx]);intervals.append({'block_quarters':block,'paths':10000,'seed':118000+block,'slope_ci95':np.quantile(draws,[.025,.975]).tolist()})
    forecast=expanding(frame)
    result={'type':'P118 daily-open proxy partial mechanism; not exact VWAP replication','n_quarters':len(frame),
            'target_period':['1993Q3','2019Q4'],'slope':observed,'bootstrap':intervals,'expanding_forecast':forecast,
            'gate_pass':bool(observed<0 and all(r['slope_ci95'][1]<0 for r in intervals) and forecast['mse_improvement']>0),
            'independent_confirmation':False,'trading_strategy_validated':False}
    (OUT/'results.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))


if __name__=='__main__':main()
