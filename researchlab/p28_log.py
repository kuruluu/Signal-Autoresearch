"""Conditional uncertainty for P28 inferred log-return convention."""
import json,hashlib,datetime
from pathlib import Path
import numpy as np
from .p28_volatility import ROOT,BASE,load,measures
from .reality_check import stationary_indices
OUT=BASE/'p28_log_001'

def register():
    OUT.mkdir(exist_ok=True)
    original=json.loads((BASE/'p28_partial_001/registration.json').read_text())
    spec={'id':'P28_log_001','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Same241month1986Jan-2006Jan originalglobaldata; inferred simple-to-log convention. Prior stored-as-log and diagnosticresults known. Conditional robustness, not independent evidence.',
    'transform':'log1p separately D1,D10,Univ; use unchangedmeasures, targets,tolerances fromfirstregistration.',
    'targets':original['targets'],'tolerances':original['tolerances'],'metric_order':original['metric_order'],
    'inference':original['inference'],
    'decision':'Allnumerical and both lowerboundsgreaterzero atall3blocks required for conditionalrobustnesspass. Passing DOESNOT establish sourceconvention, exactreplication, or permit executionpromotion without independent provenance/reconstruction. Failure preserves positivepointestimates but stops this fixed branch; no block/window/transformtuning.',
    'hashes':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),ROOT/'researchlab/p28_volatility.py',ROOT/'researchlab/reality_check.py',BASE/'p28_audit/library.xls']}}
    with (OUT/'registration.json').open('x') as f:json.dump(spec,f,indent=2)

def main():
    s=json.loads((OUT/'registration.json').read_text())
    for p,h in s['hashes'].items():
        if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise ValueError('Frozenfilechanged')
    a=load()
    if (a<=-1).any():raise ValueError('Logdomain')
    a=np.log1p(a);point=measures(a);intervals=[]
    for block in (3,12,24):
        rng=np.random.default_rng(280000+block);gaps=[];alphas=[]
        for _ in range(100):
            idx=stationary_indices(len(a),100,1/block,rng);m=measures(a[idx]);gaps.extend(m[:,0]-m[:,1]);alphas.extend(m[:,5])
        intervals.append({'block_months':block,'paths':10000,'seed':280000+block,'SR_advantage_ci95':np.quantile(gaps,[.025,.975]).tolist(),'annual_spread_alpha_ci95':np.quantile(alphas,[.025,.975]).tolist()})
    numerical=bool((np.abs(point-s['targets'])<=s['tolerances']).all())
    result={'n_months':len(a),'metrics':dict(zip(s['metric_order'],point.tolist())),'numerical_gate_pass':numerical,'bootstrap':intervals,'conditional_robustness_gate_pass':bool(numerical and all(x['SR_advantage_ci95'][0]>0 and x['annual_spread_alpha_ci95'][0]>0 for x in intervals)),'source_convention_confirmed':False,'exact_replication':False,'strategy_validated':False,'independent_confirmation':False,'execution_promotion':False}
    with (OUT/'results.json').open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps(result,indent=2))
if __name__=='__main__':
    import sys
    register() if '--register' in sys.argv else main()
