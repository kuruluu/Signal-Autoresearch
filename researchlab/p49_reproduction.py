"""P49 working-version daily appendix reproduction, not preannouncement trading."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
from .p52_reproduction import daily_table, digest, holm

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'research/replication_first'
OUT = BASE / 'p49_partial_001'
COLS = ['Lo 10'] + [f'Dec {i}' for i in range(2, 10)] + ['Hi 10']
TARGET = np.array([.20, .40, .42, .44, .46, .40, .39, .39, .37, .31])


def regression(values, event):
    """OLS constant and binary dummy with HC1 covariance, in input units."""
    y = np.asarray(values, float)
    e = np.asarray(event, bool)
    if y.ndim == 1: y = y[:, None]
    if len(e) != len(y) or not np.isfinite(y).all(): raise ValueError('Invalid panel')
    n = len(y); n1 = int(e.sum()); n0 = n-n1
    if min(n0, n1) < 2: raise ValueError('Insufficient conditional observations')
    m1 = y[e].mean(0); m0 = y[~e].mean(0)
    s1 = ((y[e]-m1)**2).sum(0)/n1**2
    s0 = ((y[~e]-m0)**2).sum(0)/n0**2
    return dict(n=n, event_n=n1, other_n=n0, intercept=m0.tolist(),
                event_mean=m1.tolist(), coefficient=(m1-m0).tolist(),
                hc1_se=np.sqrt(n/(n-2)*(s1+s0)).tolist())


def bootstrap(frame, event, block, paths=5000):
    # Common monthly resamples preserve cross-portfolio dependence and event rarity.
    e = pd.Series(np.asarray(event, bool), index=frame.index)
    sums1 = frame.mul(e, axis=0).resample('MS').sum().to_numpy()
    sums0 = frame.mul(~e, axis=0).resample('MS').sum().to_numpy()
    count1 = e.resample('MS').sum().to_numpy()
    count0 = (~e).resample('MS').sum().to_numpy()
    n, k = sums1.shape; rng = np.random.default_rng(49001+block)
    draws = np.empty((paths,k))
    for start in range(0,paths,100):
        count = min(100,paths-start); idx = np.empty((count,n),int)
        idx[:,0] = rng.integers(n,size=count)
        for j in range(1,n):
            idx[:,j] = np.where(rng.random(count)<1/block,rng.integers(n,size=count),(idx[:,j-1]+1)%n)
        c1=count1[idx].sum(1); c0=count0[idx].sum(1)
        if (c1==0).any() or (c0==0).any(): raise ValueError('Empty bootstrap group')
        draws[start:start+count]=sums1[idx].sum(1)/c1[:,None]-sums0[idx].sum(1)/c0[:,None]
    actual=np.array(regression(frame,event)['coefficient'])
    p=(1+(np.abs(draws-actual)>=np.abs(actual)).sum(0))/(paths+1)
    return dict(block_months=block,paths=paths,ci95=np.quantile(draws,[.025,.975],axis=0).T.tolist(),
                centered_two_sided_p=p.tolist(),holm_p=holm(p).tolist(),
                p_mc_se=np.sqrt(p*(1-p)/(paths+1)).tolist())


def register():
    files=[BASE/'p49_audit/sr512.pdf', BASE/'p49_audit/published.pdf',
           BASE/'p49_audit/scheduled_events.csv', BASE/'p52_audit/Portfolios_Formed_on_ME_daily.CSV',
           BASE/'p52_audit/F-F_Research_Data_Factors_daily.CSV', Path(__file__),
           ROOT/'researchlab/p52_reproduction.py']
    spec=dict(id='P49_partial_001',target='NY Fed August2013 sr512 Appendix Table B.3 size-decile dummy coefficients',
        version='Working-version numerical target. JF2015 text confirms daily size-portfolio result; final Internet Appendix unavailable (publisher403); exact final replication not claimed.',
        columns=COLS,published_coefficient_pp=TARGET.tolist(),sample=['1994-09-01','2011-03-30'],
        definition='100*(log1p(daily value-weighted total return)-log1p(French daily RF)); OLS constant plus same-session scheduled FOMC dummy; HC1 standard errors',
        calendar='Table B.1 included events (132 within sample); retain July1 1998 because missing intraday price is irrelevant to available daily prices. Excluded March26 1996 remains omitted as event but remains an ordinary daily observation. Original daily exclusion handling uncertain.',
        sensitivity='Descriptive only: include March26 1996 as scheduled full-day event, giving133. Cannot rescue primary result.',
        numerical_gate='All10 positive and all10 within0.10 percentage point of published coefficients; approximate fidelity screen not formal equivalence',
        uncertainty='5000 common stationary calendar-month resamples; blocks6/12/24; recompute10 conditional mean contrasts; centered two-sided p and Holm10; percentile95 intervals marginal, not simultaneous',
        escalation='If any Holm p in[.04,.06], repeat all blocks at20000 paths',
        robust_daily_gate='At least8 of10 positive coefficients with positive marginalCI and Holm p<=.05 at every block length; separate from numerical reproduction gate',
        limits=['2020 revised vintage is not original author data','Daily windows include announcement reaction; no intraday drift attribution',
                'Conditional resampling is not a trading Monte Carlo or predictive validation','No execution/cost or subsequent-period results; no usable signal claim'],
        hashes={str(p.relative_to(ROOT)):digest(p) for p in files})
    OUT.mkdir(exist_ok=True); path=OUT/'registration.json'
    if path.exists():
        old=json.loads(path.read_text()); assert {k:v for k,v in old.items() if k!='registered_at_utc'}==spec
        return old
    spec['registered_at_utc']=datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(spec,indent=2)); return spec


def run():
    assert (OUT/'registration.json').exists(); spec=register()
    assert not (OUT/'results.json').exists()
    r=daily_table(BASE/'p52_audit/Portfolios_Formed_on_ME_daily.CSV','Value Weighted Returns -- Daily')[COLS].loc['1994-09-01':'2011-03-30']
    rf=daily_table(BASE/'p52_audit/F-F_Research_Data_Factors_daily.CSV')['RF'].reindex(r.index)
    y=100*np.log1p(r).sub(np.log1p(rf),axis=0)
    assert np.isfinite(y.to_numpy()).all()
    c=pd.read_csv(BASE/'p49_audit/scheduled_events.csv',parse_dates=['date'])
    dates=pd.DatetimeIndex(c.loc[~c.excluded_in_table,'date'])
    assert len(dates)==132 and dates.isin(y.index).all()
    e=y.index.isin(dates); stats=regression(y,e)
    boots=[bootstrap(y,e,b) for b in [6,12,24]]
    if any(.04<=p<=.06 for b in boots for p in b['holm_p']): boots=[bootstrap(y,e,b,20000) for b in [6,12,24]]
    sensitivity=regression(y,e | (y.index==pd.Timestamp('1996-03-26')))
    coef=np.array(stats['coefficient']); match=bool(((coef>0)&(np.abs(coef-TARGET)<=.10)).all())
    robust=np.ones(10,bool)
    for b in boots: robust &= (np.array(b['holm_p'])<=.05)&(np.array(b['ci95'])[:,0]>0)&(coef>0)
    result=dict(id=spec['id'],units='percentage points of daily log excess return',columns=COLS,
        primary=stats,published=TARGET.tolist(),deviations_pp=(coef-TARGET).tolist(),
        bootstrap=boots,include_1996_03_26_sensitivity=sensitivity,
        partial_numerical_gate=match,robust_columns=robust.tolist(),robust_daily_gate=bool(robust.sum()>=8),
        headline_intraday_replicated=False,tradable_signal_validated=False,limitations=spec['limits'])
    y.assign(fomc=e).to_csv(OUT/'daily_panel.csv')
    (OUT/'results.json').write_text(json.dumps(result,indent=2))
    (OUT/'completion.json').write_text(json.dumps(dict(completed_at_utc=datetime.now(timezone.utc).isoformat(),
        hashes={p.name:digest(p) for p in OUT.iterdir() if p.is_file()}),indent=2))
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');args=p.parse_args()
    if args.run: run()
    else: register();print('Registered P49 daily appendix reproduction; no outcomes computed.')
