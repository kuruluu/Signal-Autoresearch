"""Fixed later-sample test of the registered P25 native MOM allocation."""
import json,hashlib
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import pandas as pd
from .p25_causal import ROOT,BASE,allocate,cer
from .p25_reconstruction import parse,sharpe
from .reality_check import stationary_indices

OUT=BASE/'p25_persistence_001'


def register():
    OUT.mkdir(exist_ok=True)
    paths=[Path(__file__),ROOT/'researchlab/p25_causal.py',ROOT/'researchlab/p25_reconstruction.py',
           BASE/'p08_audit/F-F_Momentum_Factor.CSV',BASE/'p08_audit/F-F_Momentum_Factor_daily.CSV']
    spec={'id':'P25_persistence_001','registered_utc':datetime.now(timezone.utc).isoformat(),
          'sample':'Native monthly MOM1927-Jan through2020-Aug inputs; score2017-Jan through2020-Aug,N44 expected; no other endpoint. Outside original2016sample, prepublication, not independentconfirmation.',
          'rule':'Unchanged p25_causal.allocate: initial120months, expanding all prior history, gamma5, training-only variance scale, same original-only control, collapsed factor exposure clip[-5,5]. No reset2017, no new parameter/window/asset.',
          'input':'Monthly native MOM outcome and previous-calendar-month daily22*mean squares. Reject missing months, zero variance or changed pinned inputhash; no fullsample scale used in allocation.',
          'metrics':'Annual SR and excessCER as previous native test, not CAGR or actual dollar account return. Report exposures and paired SR/CER gains.',
          'gate':'Both point gains positive AND both95%CI lower bounds>0 for all3/12/24-month stationarybootstrap block lengths,10000paths each,seeds25703/25712/25724; otherwise unsupported/inconclusive, no parameter rescue.',
          'bootstrap':'Paired fixed causal return rows,conditional no synthetic-history re-estimation. N44 short,24-month blocks imply very few independent blocks; no strong modern validation from passing alone.',
          'advance':'Only if gate passes, seek later bounded/pinned native data and feasible executable representation; no order/ranking. If fails, retain historical reproduction and set aside current signal transfer.',
          'hashes':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},'sealed':'No2024-2025observations'}
    with (OUT/'registration.json').open('x') as f:json.dump(spec,f,indent=2)


def run():
    spec=json.loads((OUT/'registration.json').read_text())
    for path,digest in spec['hashes'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest
    assert not (OUT/'results.json').exists()
    folder=BASE/'p08_audit';daily=parse(folder/'F-F_Momentum_Factor_daily.CSV',True);monthly=parse(folder/'F-F_Momentum_Factor.CSV',False)
    variance=22*daily.pow(2).groupby(daily.index.to_period('M')).mean();variance.index+=1
    dates=pd.period_range('1927-01','2020-08',freq='M')
    frame=pd.DataFrame({'original':monthly,'variance':variance}).reindex(dates)
    if frame.isna().any().any() or (frame.variance<=0).any():raise ValueError('Invalid native monthly panel')
    rows=allocate(frame.original,frame.variance)
    scored_dates=dates[120:];rows=rows[scored_dates>=pd.Period('2017-01',freq='M')]
    assert len(rows)==44
    values=rows[:,:2].T;sr=sharpe(values);ce=cer(values);intervals=[]
    for block in (3,12,24):
        rng=np.random.default_rng(25700+block);ds=[];dc=[]
        for offset in range(0,10000,100):
            idx=stationary_indices(len(rows),100,1/block,rng);sample=rows[idx,:2].transpose(0,2,1)
            s=sharpe(sample);c=cer(sample);ds.extend(s[:,0]-s[:,1]);dc.extend(c[:,0]-c[:,1])
        intervals.append({'block_months':block,'paths':10000,'seed':25700+block,
                          'sharpe_gain_ci95':np.quantile(ds,[.025,.975]).tolist(),
                          'cer_gain_ci95_percent':(100*np.quantile(dc,[.025,.975])).tolist()})
    passed=sr[0]>sr[1] and ce[0]>ce[1] and all(r['sharpe_gain_ci95'][0]>0 and r['cer_gain_ci95_percent'][0]>0 for r in intervals)
    result={'type':'Native MOM later-sample historical persistence, not postpublication validation',
            'n_months':len(rows),'period':['2017-01','2020-08'],
            'sharpe_combination_control':sr.tolist(),'cer_percent_combination_control':(100*ce).tolist(),
            'sharpe_gain':float(sr[0]-sr[1]),'cer_gain_pp':float(100*(ce[0]-ce[1])),
            'bootstrap':intervals,'gate_pass':bool(passed),'exposure_min':float(rows[:,2].min()),'exposure_max':float(rows[:,2].max()),
            'independent_confirmation':False,'trading_strategy_validated':False}
    (OUT/'results.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))


if __name__=='__main__':
    import sys
    register() if '--register' in sys.argv else run()
