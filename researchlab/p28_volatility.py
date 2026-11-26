"""Original P28 global log-excess decile effect, not account performance."""
from pathlib import Path
import json,hashlib,datetime
import numpy as np
import xlrd
from .reality_check import stationary_indices
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'research/replication_first'
OUT=BASE/'p28_partial_001'
DATA=BASE/'p28_audit/library.xls'

def load():
    s=xlrd.open_workbook(DATA).sheet_by_index(0)
    dates=np.array([int(s.cell_value(i,0)) for i in range(5,s.nrows)])
    expected=[y*100+m for y in range(1986,2007) for m in range(1,13) if y*100+m<=200601]
    if not np.array_equal(dates,expected):raise ValueError('Unexpected date coverage')
    a=np.array([s.row_values(i)[1:] for i in range(5,s.nrows)],float)
    if a.shape!=(241,12) or not np.isfinite(a).all():raise ValueError('Invalid panel')
    if not np.allclose(a[:,0]-a[:,9],a[:,10],atol=1.6e-5,rtol=0):raise ValueError('Stored spread inconsistent at five-decimal rounding')
    return a[:,[0,9,11]]

def measures(a):
    low,high,market=np.moveaxis(a,-1,0)
    means=a.mean(axis=-2);sd=a.std(axis=-2,ddof=1)
    m=market-market.mean(axis=-1,keepdims=True)
    def fit(y):
        beta=(m*(y-y.mean(axis=-1,keepdims=True))).sum(axis=-1)/(m*m).sum(axis=-1)
        return beta,(y.mean(axis=-1)-beta*market.mean(axis=-1))*12
    beta,alpha=fit(low);_,spreadalpha=fit(low-high)
    return np.stack([means[...,0]/sd[...,0]*np.sqrt(12),means[...,2]/sd[...,2]*np.sqrt(12),(means[...,0]-means[...,1])*12,beta,alpha,spreadalpha],axis=-1)

def register():
    OUT.mkdir(exist_ok=True)
    spec={'id':'P28_partial_001','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sample':'Original university global deciles1986Jan-2006Jan241months; April2007workingpaper. Initial5monthsD1-D5preview disclosed; no aggregate outcomes before registration.',
    'construction':'Decimal log localexcessreturns as reported; D1low,D10high,Univ equalweightedglobalbenchmark. Recompute D1-D10 from rounded legs, storedspread tolerance1.6e-5. No RFsubtraction, expconversion, ETFsubstitution or accountCAGR.',
    'metric_order':['low_SR','market_SR','annual_mean_spread','low_beta','annual_low_alpha','annual_spread_alpha'],
    'targets':[.72,.40,.059,.56,.040,.120],'tolerances':[.05,.05,.01,.05,.01,.015],
    'inference':'10000pairedstationarybootstrap paths per3/12/24month expectedblock; seeds280000+block. Refit CAPM ineachdraw. Two-sided95percentileCI for lowSR-minus-marketSR and annualspreadalpha. Jointgate requires all numerical tolerances and positive lowerbounds for both quantities at all3blocks. Nootherdecile/window/blocksearch. Conditional aggregate-return sampling, notstockpanel reformation.',
    'limits':'Original historical effect reproduction, notindependentconfirmation, executableaccount or costs. Native holdings/turnover/borrow absent. Gatepass permits feasibilityaudit only, no rankings or orders.',
    'hashes':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),ROOT/'researchlab/reality_check.py',DATA]}}
    with (OUT/'registration.json').open('x') as f:json.dump(spec,f,indent=2)

def main():
    spec=json.loads((OUT/'registration.json').read_text())
    for p,h in spec['hashes'].items():
        if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise ValueError('Frozen file changed')
    if (OUT/'results.json').exists():raise ValueError('Already evaluated')
    a=load();point=measures(a);intervals=[]
    for block in (3,12,24):
        rng=np.random.default_rng(280000+block);gaps=[];alphas=[]
        for batch in range(100):
            idx=stationary_indices(len(a),100,1/block,rng);m=measures(a[idx]);gaps.extend(m[:,0]-m[:,1]);alphas.extend(m[:,5])
        intervals.append({'block_months':block,'paths':10000,'seed':280000+block,'SR_advantage_ci95':np.quantile(gaps,[.025,.975]).tolist(),'annual_spread_alpha_ci95':np.quantile(alphas,[.025,.975]).tolist()})
    numerical=bool((np.abs(point-spec['targets'])<=spec['tolerances']).all())
    result={'n_months':len(a),'metrics':dict(zip(spec['metric_order'],point.tolist())),'numerical_gate_pass':numerical,'bootstrap':intervals,'advance_to_execution_audit':bool(numerical and all(x['SR_advantage_ci95'][0]>0 and x['annual_spread_alpha_ci95'][0]>0 for x in intervals)),'independent_confirmation':False,'strategy_validated':False}
    with (OUT/'results.json').open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps(result,indent=2))
if __name__=='__main__':
    import sys
    register() if '--register' in sys.argv else main()
