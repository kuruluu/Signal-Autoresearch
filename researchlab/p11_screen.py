"""Frozen causal monthly trend screen in synthetic adjusted units."""
import json,hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from .reality_check import stationary_indices

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'research/replication_first/p11_contemporary_001'


def targets(close):
    # Only a completed observed month can change the next session's target.
    month=close.index.to_period('M');ends=np.flatnonzero(np.r_[month[:-1]!=month[1:],False])
    levels=close.iloc[ends];average=levels.rolling(10).mean();events={};state=0
    for date,level,mean in zip(levels.index,levels,average):
        if np.isfinite(mean):
            if level>mean:state=1
            elif level<mean:state=0
            events[date]=state
    return pd.Series(events).reindex(close.index).ffill().shift(1).fillna(0)


def simulate(frame,target,cost_bps):
    c=cost_bps/10000;shares=0.;cash=1.;previous=1.;rows=[];trades=0
    for date,bar in frame.iterrows():
        desired=float(target.loc[date]);opening=cash+shares*bar.adj_open
        if desired==1 and shares==0:
            shares=cash/(bar.adj_open*(1+c));cash=0.;trades+=1
        elif desired==0 and shares>0:
            cash=shares*bar.adj_open*(1-c);shares=0.;trades+=1
        equity=cash+shares*bar.adj_close
        rows.append(equity/previous-1);previous=equity
    return pd.Series(rows,index=frame.index),trades


def metrics(returns,years):
    equity=np.cumprod(1+np.asarray(returns),axis=-1)
    peak=np.maximum.accumulate(np.maximum(equity,1),axis=-1)
    return equity[...,-1]**(1/years)-1,(1-equity/peak).max(axis=-1)


def resample(panel,block,paths=10000):
    groups=[g.to_numpy().T for _,g in panel.groupby(panel.index.to_period('M'))]
    n=len(groups);width=max(g.shape[1] for g in groups)
    padded=np.zeros((n,3,width))
    for i,g in enumerate(groups):padded[i,:,:g.shape[1]]=g
    rng=np.random.default_rng(11000+block);cagrs=[];drawdowns=[]
    for offset in range(0,paths,100):
        idx=stationary_indices(n,min(100,paths-offset),1/block,rng)
        values=padded[idx].transpose(0,2,1,3).reshape(len(idx),3,-1)
        cg,dd=metrics(values,n/12);cagrs.extend(cg);drawdowns.extend(dd)
    cg=np.asarray(cagrs);dd=np.asarray(drawdowns)
    return {'block_months':block,'paths':paths,'seed':11000+block,
            'drawdown_reduction_ci95':np.quantile(dd[:,1]-dd[:,0],[.025,.975]).tolist(),
            'strategy_cagr_5_50_percentile':np.quantile(cg[:,0],[.05,.5]).tolist(),
            'strategy_drawdown_95_percentile':float(np.quantile(dd[:,0],.95))}


def main():
    spec=json.loads((OUT/'registration.json').read_text())
    for name,digest in spec['hashes'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest
    assert not (OUT/'results.json').exists()
    full=pd.read_csv(ROOT/'research/data/SPY.csv',index_col='date',parse_dates=True)
    assert full.index.max()<pd.Timestamp('2024-01-01')
    target=targets(full.adj_close);frame=full.loc['2008-01-02':'2023-12-29']
    strategy,trades=simulate(frame,target,5);stress,_=simulate(frame,target,10)
    bh,_=simulate(frame,pd.Series(1,index=frame.index),5)
    underlying=full.adj_close.pct_change().reindex(frame.index)
    panel=pd.DataFrame({'strategy':strategy,'buyhold':bh,'fixed50':underlying*.5})
    years=(frame.index[-1]-frame.index[0]).days/365.25
    summary={}
    for name,ret in [*panel.items(),('stress10bps',stress)]:
        cg,dd=metrics(ret.to_numpy(),years);summary[name]={'cagr':float(cg),'max_drawdown':float(dd),'ending_10000':float(10000*np.prod(1+ret))}
    intervals=[resample(panel,b) for b in (3,12,24)]
    s=summary['strategy'];b=summary['buyhold'];stress=summary['stress10bps']
    passed=s['cagr']>0 and s['cagr']>=.6*b['cagr'] and s['max_drawdown']<=.75*b['max_drawdown'] and all(r['drawdown_reduction_ci95'][0]>0 for r in intervals)
    stress_pass=stress['cagr']>0 and stress['max_drawdown']<b['max_drawdown']
    result={'type':'Synthetic adjusted-unit contemporary screen, not executable validation','sessions':len(frame),'trades':trades,'summary':summary,'bootstrap':intervals,'primary_gate_pass':bool(passed),'stress_gate_pass':bool(stress_pass),'advance_to_raw_account_test':bool(passed and stress_pass),'independent_confirmation':False,'trading_strategy_validated':False}
    (OUT/'results.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))


if __name__=='__main__':main()
