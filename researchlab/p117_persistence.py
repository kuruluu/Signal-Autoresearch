"""Registered P117 fixed-window post-publication persistence checks."""
import json,hashlib
from datetime import datetime,timezone
from pathlib import Path
import pandas as pd
from .p117_reconstruction import BASE,months,bootstrap

OUT=BASE/'p117_persistence_001'


def register():
    OUT.mkdir(exist_ok=True)
    path=OUT/'registration.json'
    if path.exists():raise ValueError('Registration already exists; do not overwrite')
    spec={'id':'P117_persistence_001','registered_utc':datetime.now(timezone.utc).isoformat(),
          'effect':'Fixed last trading day plus next first three trading days; no window search',
          'primary':'1989-01-01 to 2023-11-21; same extraction omits first/last boundary months, hence Feb1989-Oct2023 receiving months',
          'recent_gate':'Receiving months Jan2012-Oct2023 subset of primary; no reoptimization',
          'estimators':'Mean sum of four simple close-to-close price returns; contrast minus four times pooled non-TOM daily mean',
          'bootstrap':'10000 stationary monthly resamples, blocks3/12/24, seeds117003/117012/117024; resample TOM sum and rest sum/count jointly within each fixed period',
          'advance':'Both primary AND recent contrast 95% CI lower bounds strictly positive for all three blocks. Otherwise set aside this fixed transfer, no tuning.',
          'limits':'Already viewed Dow periods; post-publication historical persistence, not fresh independent confirmation or executable ETF evidence. DJIA price index omits dividends, costs and closing fills.',
          'sealed':'No 2024-2025 observations',
          'hashes':{str(p.relative_to(BASE.parent.parent)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),BASE.parent.parent/'researchlab/p117_reconstruction.py',BASE/'p50_audit/DJIA.csv']}}
    path.write_text(json.dumps(spec,indent=2))


def run():
    spec=json.loads((OUT/'registration.json').read_text())
    for rel,digest in spec['hashes'].items():
        assert hashlib.sha256((BASE.parent.parent/rel).read_bytes()).hexdigest()==digest
    assert not (OUT/'results.json').exists()
    price=pd.read_csv(BASE/'p50_audit/DJIA.csv',index_col=0,parse_dates=True).value
    frame=months(price,'1989-01-01','2023-11-21');results={}
    for label,g in [('post_publication',frame),('recent_2012_onward',frame[frame.month>='2012-01'])]:
        intervals=[bootstrap(g,b) for b in (3,12,24)]
        results[label]={'n_months':len(g),'first':g.month.iloc[0],'last':g.month.iloc[-1],
                        'four_day_mean_percent':float(100*g.tom_sum.mean()),
                        'contrast_percent':float(100*(g.tom_sum.mean()-4*g.rest_sum.sum()/g.rest_n.sum())),
                        'bootstrap':intervals,'gate_pass':all(x['contrast_ci95_percent'][0]>0 for x in intervals)}
    results['advance_to_ETF_execution_audit']=all(r['gate_pass'] for r in results.values())
    results['independent_confirmation']=False;results['trading_strategy_validated']=False
    (OUT/'results.json').write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2))


if __name__=='__main__':
    import sys
    register() if '--register' in sys.argv else run()
