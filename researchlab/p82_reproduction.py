"""Registered partial reconstruction of P82 BLL26 mean-return family."""
import argparse,json
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import pandas as pd
from .p82_rules import positions
from .reality_check import stationary_indices
from .p52_reproduction import digest

ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'research/replication_first';OUT=BASE/'p82_partial_001'


def register():
    paths=[Path(__file__),ROOT/'researchlab/p82_rules.py',ROOT/'researchlab/reality_check.py',BASE/'p50_audit/DJIA.csv',BASE/'p82_audit/published.pdf']
    spec=dict(id='P82_partial_001',target='PublishedTableIII BLL26 meancriterion,1897-1986/1987-1996/1897-1996 jointly',
        target_annual_percent=[10.11,8.63,9.39],target_white_p=[0,.154,0],
        inputs='ThirdpartyhistoricalDowarchive; originalsource/countdifferences unresolved; partialreproduction only. Restrict1897-1996prices first,250observationwarmup,continuousstates across1987boundary.',
        rule_definition='p82_rules.py26rules; VMAneutral insideband; FMAentry into nonzero bandstate triggers10sessionhold,eventsignored whileholding; TRBpriorwindow excludingcurrent,10sessionhold. Ambiguousoriginalstates explicitly assumed.',
        performance='log1p(simpleprice_return*previouscloseposition),nullbenchmark0; nofees/RF/dividends.252*meandailylogreturn,notCAGR. Originalfamily26only,not7846.',
        bootstrap='5000 common stationary daily-index resamples of fixed26performancevectors; q.1,seed82001; centered maxmean WhiteRealityCheck, finitecorrection(1+exceedances)/(B+1). Nominal pfor observedbest only. No future rule selectionfor trading.',
        gates='Approximate numerical match if all3bestannualmeanswithin2percentagepoints and historical2Whitep<=.05,laterWhitep>.05. Unmatched means or inference=>inconsistentpartialimplementation; no retuning. This is replication criterion,not signal usefulness.',
        limits=['PriorP50alreadyinspectedDowperformance','Noindependentconfirmation','NoETFexecutableclaim','OriginalB500versusour5000paths;MCuncertaintydisclosed'],
        hashes={str(p.relative_to(ROOT)):digest(p) for p in paths})
    OUT.mkdir(exist_ok=True);f=OUT/'registration.json'
    if f.exists():
        old=json.loads(f.read_text());assert {k:v for k,v in old.items() if k!='registered_at_utc'}==spec;return spec
    spec['registered_at_utc']=datetime.now(timezone.utc).isoformat();f.write_text(json.dumps(spec,indent=2));return spec


def inference(v,paths=5000):
    values=v.to_numpy();n,k=values.shape;means=values.mean(0);winner=int(means.argmax());observed=np.sqrt(n)*means[winner];rng=np.random.default_rng(82001)
    family=nominal=0
    for offset in range(0,paths,25):
        count=min(25,paths-offset);idx=stationary_indices(n,count,.1,rng)
        boot=values[idx].mean(1)-means
        family+=int((np.sqrt(n)*boot.max(1)>=observed).sum());nominal+=int((np.sqrt(n)*boot[:,winner]>=observed).sum())
    p=(1+family)/(paths+1)
    return dict(n=n,best_rule=v.columns[winner],best_annual_percent=float(25200*means[winner]),white_p=p,nominal_p=(1+nominal)/(paths+1),paths=paths,p_mc_se=float(np.sqrt(p*(1-p)/(paths+1))))


def run():
    assert (OUT/'registration.json').exists();spec=register();assert not (OUT/'results.json').exists()
    f=pd.read_csv(BASE/'p50_audit/DJIA.csv',index_col=0,parse_dates=True);price=f.iloc[:,0].loc['1897-01-01':'1996-12-31']
    assert price.index.is_unique and price.index.is_monotonic_increasing
    states=positions(price);ret=price.pct_change(fill_method=None);performance=np.log1p(states.shift(1).mul(ret,axis=0)).iloc[250:]
    assert np.isfinite(performance.to_numpy()).all()
    results=[]
    for start,end in [('1897','1986'),('1987','1996'),('1897','1996')]:
        r=inference(performance.loc[start:end]);r['period']=[start,end];results.append(r)
        (OUT/'progress.json').write_text(json.dumps(results,indent=2));print(r,flush=True)
    match=all(abs(r['best_annual_percent']-target)<=2 for r,target in zip(results,spec['target_annual_percent'])) and results[0]['white_p']<=.05 and results[1]['white_p']>.05 and results[2]['white_p']<=.05
    (OUT/'results.json').write_text(json.dumps(dict(periods=results,partial_match=bool(match),tradable_signal_validated=False),indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');a=p.parse_args()
    if a.run:run()
    else:register();print('Registered; no market outcomes computed.')
