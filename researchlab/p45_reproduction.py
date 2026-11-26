"""Registered partial reproduction of FEARS Table2 column4."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
from .bz2007_reproduction import ROOT, BASE, digest
from .reality_check import stationary_indices

INPUT=BASE/'p45_audit'
OUT=BASE/'p45_partial_001'


def assemble(prices, fears, vix, epu, ads):
    """Difference macro series on calendar days before joining market sessions."""
    returns=prices.pct_change(fill_method=None)
    frame=pd.DataFrame({'fears':fears,'vix':vix,'epu_change':epu.diff(),
                        'ads_change':ads.diff()}).reindex(prices.index)
    for lag in range(6): frame[f'return_lag{lag}']=returns.shift(lag)
    frame['future2']=(1+returns.shift(-1))*(1+returns.shift(-2))-1
    return frame.reindex(fears.index).dropna()


def load_panel():
    def market(name):
        f=pd.DataFrame(json.loads((INPUT/name).read_text()))
        return pd.Series(f.close.to_numpy(),index=pd.to_datetime(f.date))
    f=pd.read_csv(INPUT/'fears_post_20140512.csv')
    fears=pd.Series(f.fears30.to_numpy(),index=pd.to_datetime(f.date))
    e=pd.read_csv(INPUT/'EPU_archive_20120826.csv')
    epu=pd.Series(e.daily_policy_index.to_numpy(),index=pd.to_datetime(e[['year','month','day']]))
    a=pd.read_csv(INPUT/'ADS_20130110_2004_2011.csv')
    ads=pd.Series(a.ADS.to_numpy(),index=pd.to_datetime(a.date))
    return assemble(market('GSPC_2004_2011.json'),fears,market('VIX_2004_2011.json'),epu,ads)


def estimate(frame,paths=5000):
    y=frame.future2.to_numpy()
    columns=[c for c in frame if c!='future2']
    raw=frame[columns].to_numpy();scale=raw.std(axis=0)
    x=np.column_stack([np.ones(len(raw)),raw/scale])
    beta=np.linalg.lstsq(x,y,rcond=None)[0]
    position=1+columns.index('fears')
    draws=[]
    for block in (5,10,20):
        indices=stationary_indices(len(y),paths,1/block,np.random.default_rng(45000+block))
        coefficients=[]
        for idx in indices:
            coefficients.append(np.linalg.lstsq(x[idx],y[idx],rcond=None)[0][position]/scale[position-1])
        coefficients=np.asarray(coefficients)
        draws.append({'block_sessions':block,'paths':paths,
                      'bootstrap_se':float(coefficients.std(ddof=1)),
                      'ci95':np.quantile(coefficients,[.025,.975]).tolist()})
        print('Completed block',block,flush=True)
    coef=float(beta[position]/scale[position-1])
    return {'n':len(frame),'first':str(frame.index[0].date()),'last':str(frame.index[-1].date()),
            'fears_coefficient':coef,'published_coefficient':.00409,
            'published_bootstrap_se':.00137,'bootstrap':draws,
            'approximate_numeric_match':bool(abs(coef-.00409)<=.0015 and abs(draws[0]['bootstrap_se']-.00137)<=.0007),
            'positive_effect_robust':bool(all(row['ci95'][0]>0 for row in draws)),
            'scope':'Partial controlled descriptive reproduction, not an executable or causal forecast test.'}


def register():
    files=[Path(__file__),ROOT/'researchlab/reality_check.py',INPUT/'published.pdf',
           *[INPUT/n for n in ['fears_post_20140512.csv','GSPC_2004_2011.json','VIX_2004_2011.json',
                              'EPU_archive_20120826.csv','ADS_20130110_2004_2011.csv']]]
    spec={'id':'P45_partial_001','registered_at':datetime.now(timezone.utc).isoformat(),
          'primary':'Published Table2col4 FEARS coefficient.00409,bootSE.00137,N1889',
          'response':'Simple compounded S&P price return from close_t through close_t+2, session horizons, no weekend calendar shift',
          'controls':'Constant; FEARS30; contemporaneous VIX level; calendar-day first difference EPU and ADS; current simple return and5sessionlags',
          'sample':'Author FEARS dates2004-07-01 through2011-12-30; intersect complete controls and availablefuture2; expected1889pairs',
          'inference':'5000pairedstationaryrow bootstrap fits each block5/10/20sessions, seeds45005/45010/45020; fixed source index; modern dependence inference, not exactauthor unspecifiedbootstrap',
          'approximate_gate':'coefficient within.0015 of.00409 and block5SE within.0007 of.00137; positiveeffect robust only if all3CI95lower>0',
          'deviations':['2012EPU and2013ADS archival vintages; YahooSPX/VIX history not originalauthor inputvintage',
                        'Originalbootstrapspecification unspecified; modernstationarypairedbootstrap declared',
                        'Cumulative return assumedcompound; macro changes takenonecalendarday, notmarket-sessiongap; definitions needauthorcode for exactclaim'],
          'execution_caveat':'FEARSday ends midnightPacific after marketclose. This regression includes return intervals before fullsignal availability; no causal or tradableclaim. Macrocontrols retrospective.',
          'files':{str(f.relative_to(ROOT)):digest(f) for f in files}}
    OUT.mkdir(exist_ok=True)
    with (OUT/'registration.json').open('x') as f:json.dump(spec,f,indent=2)


def run():
    spec=json.loads((OUT/'registration.json').read_text())
    for file,expected in spec['files'].items():assert digest(ROOT/file)==expected,file
    frame=load_panel();assert len(frame)==1889
    result=estimate(frame)
    with (OUT/'results.json').open('x') as f:json.dump(result,f,indent=2)
    frame.to_csv(OUT/'scored_panel.csv')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['register','run'])
    {'register':register,'run':run}[p.parse_args().action]()
