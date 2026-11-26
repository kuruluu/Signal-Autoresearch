"""One prespecified P28 log-conversion diagnostic; not verified native correction."""
from pathlib import Path
import json,hashlib,datetime
import numpy as np
from .p28_volatility import load,measures,ROOT,BASE
OUT=BASE/'p28_convention_001'

def register():
    OUT.mkdir(exist_ok=True)
    first=json.loads((BASE/'p28_partial_001/registration.json').read_text())
    spec={'id':'P28_convention_001','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'reason':'Paper explicitly uses logtransformed localexcessreturns. Workbook says equalweightedreturns, no log label or cell notes, percentageformat not decisive. Firststored-as-log numericaltestfailed. One diagnostic treats storedseries as simple excess and applies log1p separately to D1,D10,Univ. Not proven source correction.',
    'fixed_transform':'np.log1p ofeachstoredleg andUniv, then unchanged metrics. Do NOT log1p ofspread. Same241months,targets,tolerances; nooffset/endpoints/othertransforms searched.',
    'targets':first['targets'],'tolerances':first['tolerances'],'metric_order':first['metric_order'],
    'decision':'If numericalmatch improves, evidence of convention mismatch only. Never promote solely from matching published numbers; require independent source confirmation or reconstruct correct stocklevel excess logaggregation. If fails, preserve both without searching transforms. No repeatedbootstrap required for this source diagnosis.',
    'limits':'log1p(simpleexcess) differs from logtotal minuslogriskfree; mean(logindividual) differs from log(meanindividual). Missing perstock/localRFinputs prevents resolving aggregation exactly. Priorresults known; diagnostic notindependentconfirmation or validatedreplication.',
    'hashes':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),ROOT/'researchlab/p28_volatility.py',BASE/'p28_audit/library.xls']}}
    with (OUT/'registration.json').open('x') as f:json.dump(spec,f,indent=2)

def main():
    s=json.loads((OUT/'registration.json').read_text())
    for p,h in s['hashes'].items():
        if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise ValueError('Frozenfilechanged')
    a=load()
    if (a<=-1).any():raise ValueError('Logdomain')
    m=measures(np.log1p(a))
    result={'metrics':dict(zip(s['metric_order'],m.tolist())),'numerical_tolerances_met':bool((np.abs(m-s['targets'])<=s['tolerances']).all()),'source_convention_confirmed':False,'exact_replication':False,'strategy_validated':False,'advance_to_execution':False}
    with (OUT/'results.json').open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps(result,indent=2))
if __name__=='__main__':
    import sys
    register() if '--register' in sys.argv else main()
