"""Prospective partial reproduction of one published conditional-return contrast."""
import argparse
import json
from datetime import datetime, timezone
import numpy as np
import pandas as pd
from .p52_reproduction import ROOT, digest

INPUT=ROOT/'research/replication_first/p50_audit'
OUT=ROOT/'research/replication_first/p50_partial_001'


def observations(price,window=150):
    average=price.rolling(window).mean()
    state=np.sign(price-average).shift(1)
    return pd.DataFrame({'log_return':np.log(price).diff(),'state':state}).dropna()


def estimate(frame):
    y=frame.log_return;buy=y[frame.state>0];sell=y[frame.state<0]
    if min(len(buy),len(sell))<2:raise ValueError('Insufficient conditional observations')
    variance=y.var(ddof=1);mu=y.mean();n=len(y)
    gap=float(buy.mean()-sell.mean())
    return dict(n=n,buy_n=len(buy),sell_n=len(sell),neutral_n=int((frame.state==0).sum()),
        buy_mean=float(buy.mean()),sell_mean=float(sell.mean()),gap=gap,
        pooled_t=gap/np.sqrt(variance*(1/len(buy)+1/len(sell))),
        buy_t=float((buy.mean()-mu)/np.sqrt(variance*(1/n+1/len(buy)))),
        sell_t=float((sell.mean()-mu)/np.sqrt(variance*(1/n+1/len(sell)))),
        buy_std=float(buy.std(ddof=1)),sell_std=float(sell.std(ddof=1)))


def block_inference(frame,block,paths=5000):
    # Resample calendar-month sufficient statistics jointly, preserving within-month order/state pairing.
    f=pd.DataFrame({'buy_sum':frame.log_return.where(frame.state>0,0),
        'buy_n':(frame.state>0).astype(int),'sell_sum':frame.log_return.where(frame.state<0,0),
        'sell_n':(frame.state<0).astype(int)})
    values=f.groupby(f.index.to_period('M')).sum().to_numpy();n=len(values)
    rng=np.random.default_rng(50001+block);draws=np.empty(paths)
    for start in range(0,paths,100):
        count=min(100,paths-start);idx=np.empty((count,n),int);idx[:,0]=rng.integers(n,size=count)
        for j in range(1,n):
            idx[:,j]=np.where(rng.random(count)<1/block,rng.integers(n,size=count),(idx[:,j-1]+1)%n)
        sums=values[idx].sum(axis=1)
        if (sums[:,[1,3]]<=0).any():raise ValueError('Empty conditional bootstrap sample')
        draws[start:start+count]=sums[:,0]/sums[:,1]-sums[:,2]/sums[:,3]
    actual=estimate(frame)['gap'];p=float((1+(np.abs(draws-actual)>=abs(actual)).sum())/(paths+1))
    return dict(block_months=block,paths=paths,gap_95=np.quantile(draws,[.025,.975]).tolist(),
        centered_two_sided_p=p,mc_se=float(np.sqrt(p*(1-p)/(paths+1))),
        conditional_gap_sd=float(draws.std(ddof=1)))


def register():
    spec=dict(id='P50_partial_001',target='Published 1992 Table II Panel A VMA(1,150,0), printed p1739',
        published=dict(buy_n=14866,sell_n=9806,buy_mean=.00040,sell_mean=-.00022,gap=.00062,pooled_t=4.39590),
        sample=['1897-01-01','1986-12-31'],window=150,
        definition='Daily log close-to-close index return at t classified by sign(close-SMA150) at t-1; SMA includes current close; equal values neutral',
        warmup='Restrict levels to 1897-1986 before computing SMA; first 150 observations cannot have lagged valid signal',
        sessions='Keep all supplied historical sessions, including Saturdays and closures; do not forward-fill',
        original_inference='Published full-sample daily-return variance pooled into sqrt(var/Nbuy+var/Nsell); ddof1; same formula for conditional versus unconditional means',
        subperiods=[['1897-01-01','1914-07-30'],['1915-01-01','1938-12-31'],['1939-01-01','1962-06-30'],['1962-07-01','1986-12-31']],
        subperiod_role='Descriptive diagnostics using continuous full-sample signal warmup; not additional discovery claims or attempts to reproduce subperiod counts',
        numerical_tolerances=dict(each_mean_abs=.00010,gap_abs=.00015,pooled_t_abs=1.0,
            reason='Prospective approximate-match screen for nonidentical source and warmup; not formal equivalence',
            rule='Positive gap and all mean/gap/t screens pass => partial numerical reproduction; otherwise inconsistent under this implementation; counts always disclosed, exact replication impossible'),
        bootstrap='5000 joint stationary calendar-month-block samples of fixed state/return sufficient statistics, blocks6/12/24, seed50001+block; conditional mean difference recomputed each path; single primary contrast, no multiplicity across descriptive subperiods; report every block',
        escalation='If any primary p in [.04,.06], use 20000 paths for all blocks',
        limits=['Third-party source differs from original authors and has unresolved observation-count discrepancy',
          'Lag and warmup conventions explicit assumptions; no change after seeing result',
          'No random-walk/AR/GARCH null-model reproduction claimed',
          'Fixed-state block resampling is conditional uncertainty, not a fitted predictive-model validation',
          'Conditional buy-minus-sell log return is not portfolio annual return or net alpha',
          'Historical source differences and nonstationarity limit interpretation'],
        hashes={str(INPUT/x):digest(INPUT/x) for x in ['DJIA.csv','published.pdf','manifest.json']},
        code_sha256=digest(__file__),sealed_access=False)
    OUT.mkdir(exist_ok=True);f=OUT/'registration.json'
    if f.exists():
        old=json.loads(f.read_text());assert {k:v for k,v in old.items() if k!='registered_at_utc'}==spec
        return old
    spec['registered_at_utc']=datetime.now(timezone.utc).isoformat();f.write_text(json.dumps(spec,indent=2));return spec


def run():
    assert (OUT/'registration.json').exists();spec=register();assert not (OUT/'results.json').exists()
    data=pd.read_csv(INPUT/'DJIA.csv',parse_dates=['date']).set_index('date')
    assert data.index.is_unique and data.index.is_monotonic_increasing and data.index.max()<pd.Timestamp('2024-01-01')
    price=data.value.loc['1897':'1986'];assert price.gt(0).all() and not price.isna().any()
    f=observations(price);e=estimate(f)
    checks=dict(means=abs(e['buy_mean']-.00040)<=.00010 and abs(e['sell_mean']+.00022)<=.00010,
        gap=abs(e['gap']-.00062)<=.00015,pooled_t=abs(e['pooled_t']-4.39590)<=1,positive=e['gap']>0)
    inf=[block_inference(f,b) for b in [6,12,24]]
    if any(.04<=x['centered_two_sided_p']<=.06 for x in inf):inf=[block_inference(f,b,20000) for b in [6,12,24]]
    result=dict(verdict='Partial numerical reproduction' if all(checks.values()) else 'Numerically inconsistent under registered implementation',
        estimate=e,published=spec['published'],checks={k:bool(v) for k,v in checks.items()},bootstrap=inf,
        subperiods=[dict(start=a,end=b,**estimate(f.loc[a:b])) for a,b in spec['subperiods']],
        first_return=str(f.index[0].date()),last_return=str(f.index[-1].date()),eligible_signal=False,limitations=spec['limits'])
    f.to_csv(OUT/'conditional_daily.csv');(OUT/'results.json').write_text(json.dumps(result,indent=2))
    (OUT/'completion.json').write_text(json.dumps(dict(completed_at_utc=datetime.now(timezone.utc).isoformat(),hashes={x.name:digest(x) for x in OUT.iterdir() if x.is_file()}),indent=2))
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');a=p.parse_args()
    if a.run:run()
    else:register();print('Registered P50 partial reproduction; no outcomes computed.')
