"""Separate registered persistence gate, before ETF signal development."""
import argparse,json
from datetime import datetime,timezone
import pandas as pd
from .p50_reproduction import INPUT,observations,estimate,block_inference
from .p52_reproduction import ROOT,digest
OUT=ROOT/'research/replication_first/p50_persistence_001'

def register():
    files=[INPUT/'DJIA.csv',ROOT/'researchlab/p50_reproduction.py']
    spec=dict(id='P50_persistence_001',parent='P50_partial_001',stage='Later-sample mechanism persistence, not independent confirmation',
        sample=['1987-01-01','2022-12-31'],warmup='1986 index levels; continuous lagged 150-session rule; retain all observed sessions',
        primary='Difference in conditional daily log returns: prior-close above SMA150 minus below SMA150',
        gate='Gap >=0.00020 (2 bps/day) and all 6/12/24-month bootstrap lower95 bounds >0 and centered two-sided p<=.05',
        gate_reason='Require a nontrivial surviving gross effect before spending an ETF execution stage; not a profitability threshold',
        inference='Fixed-state calendar-month sufficient-statistic bootstrap, 5000 paths seed50001+block; 20000 all blocks if any p in [.04,.06]; one primary contrast',
        failure_action='Set aside P50 trading-signal branch; do not retune lookback or promote variance differences as a new success',
        limits=['Full calendar years through 2022 deliberately exclude incomplete 2023 and all sealed years',
            'Historical data and published follow-up findings already inspected: no fresh confirmation claim',
            'Source switches from Pinnacle to quantmod in 1992; cannot attribute discrepancies solely to economics',
            'Conditional log-return spread is not realized portfolio return; no costs or ETF implementation'],
        hashes={str(x):digest(x) for x in files},code_hash=digest(__file__))
    OUT.mkdir(exist_ok=True);f=OUT/'registration.json'
    if f.exists():
        prev=json.loads(f.read_text());assert {k:v for k,v in prev.items() if k!='registered_at_utc'}==spec
        return prev
    spec['registered_at_utc']=datetime.now(timezone.utc).isoformat();f.write_text(json.dumps(spec,indent=2));return spec

def run():
    assert (OUT/'registration.json').exists();spec=register();assert not (OUT/'results.json').exists()
    p=pd.read_csv(INPUT/'DJIA.csv',index_col='date',parse_dates=True).value
    assert p.index.max()<pd.Timestamp('2024-01-01')
    f=observations(p.loc['1986':'2022']).loc['1987':'2022'];e=estimate(f)
    inf=[block_inference(f,b) for b in [6,12,24]]
    if any(.04<=x['centered_two_sided_p']<=.06 for x in inf):inf=[block_inference(f,b,20000) for b in [6,12,24]]
    passed=e['gap']>=.00020 and all(x['gap_95'][0]>0 and x['centered_two_sided_p']<=.05 for x in inf)
    result=dict(verdict='Supports proceeding to ETF transfer' if passed else 'Fails registered persistence gate',estimate=e,bootstrap=inf,eligible_signal=False,limitations=spec['limits'])
    f.to_csv(OUT/'conditional_daily.csv');(OUT/'results.json').write_text(json.dumps(result,indent=2))
    (OUT/'completion.json').write_text(json.dumps(dict(completed_at_utc=datetime.now(timezone.utc).isoformat(),hashes={x.name:digest(x) for x in OUT.iterdir() if x.is_file()}),indent=2))
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');a=p.parse_args()
    if a.run:run()
    else:register();print('Registered later-period persistence gate; no outcomes computed.')
