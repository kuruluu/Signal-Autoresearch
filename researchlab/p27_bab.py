"""P27 original author BAB aggregate partial reconstruction, not broker returns."""
from pathlib import Path
import json,hashlib,datetime,re
import numpy as np
from openpyxl import load_workbook
from .reality_check import stationary_indices
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'research/replication_first';OUT=BASE/'p27_partial_001'
FILES=[BASE/'p27_audit/original.xlsx',BASE/'p24_inputs/monthly_archive.txt',BASE/'p08_audit/F-F_Momentum_Factor.CSV']
def monthly(path,n):
    out={}
    for line in path.read_text().splitlines():
        if re.match(r'^\d{6},',line):
            a=line.split(',');date=int(a[0]);v=np.array([float(x)/100 for x in a[1:]])
            if len(v)!=n or date in out or not np.isfinite(v).all() or (abs(v)>=.99).any():raise ValueError('Invalid factor row')
            out[date]=v
    return out

def load():
    w=load_workbook(FILES[0],read_only=True,data_only=True);s=w['BAB factors'];rows=list(s.values)
    if rows[10][1]!='U.S. Equities':raise ValueError('Wrong header')
    pairs=[(r[0],r[1]) for r in rows[11:] if isinstance(r[0],int) and r[1] is not None];w.close()
    dates=np.array([x[0] for x in pairs]);y=np.array([x[1] for x in pairs],float)
    expected=np.array([yr*100+m for yr in range(1929,2013) for m in range(1,13) if 192904<=yr*100+m<=201203])
    if not np.array_equal(dates,expected) or not np.isfinite(y).all() or len(y)!=996:raise ValueError('Unexpected US coverage')
    ff=monthly(FILES[1],4);mom=monthly(FILES[2],1)
    x=np.array([[1,*ff[d][:3],mom[d][0]] for d in dates])
    return dates,y,x

def register():
    OUT.mkdir(exist_ok=True)
    spec={'id':'P27_partial_001','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sample':'US BAB April1929-March2012 996months, original workbook decimal percentage-formatted cells. Missing1926-early1929 not filled; unresolved construction/version discrepancy. Partial, not exact replication.',
    'targets':{'monthly_mean':.007,'annual_sd':.1075,'annual_sharpe':.78,'ff3_monthly_alpha':.0073,'ff4_monthly_alpha':.0055},
    'numerical_tolerances':{'monthly_mean':.0015,'annual_sd':.015,'annual_sharpe':.12,'ff3_monthly_alpha':.0015,'ff4_monthly_alpha':.0015},
    'construction':'US original BAB zero-investment excess return; do not subtract RF again. FF3 Mkt-RF SMB HML official201507 and momentum202008 vintage. OLS intercept plus factors. FF vintage mismatch explicit.',
    'inference':'Paired stationary bootstrap10000 paths per3/12/24month expected blocks,seeds270000+block. Refit four-factor OLS per draw. 95% percentile intervals on annual arithmetic mean and monthly FF4alpha. Joint advancement gate: all numerical tolerances and all six lower bounds positive. No country/asset/endpoints/weights search.',
    'limits':'Already historical research data; author construction, not causal portfolio rebuild or independent confirmation. Financing assumptions embedded in factor differ from broker credit; no costs/borrow/constituents supplied. Passing permits execution feasibility audit only. No trading/ranking admission.',
    'hashes':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),ROOT/'researchlab/reality_check.py',*FILES]}}
    with (OUT/'registration.json').open('x') as f:json.dump(spec,f,indent=2)

def main():
    spec=json.loads((OUT/'registration.json').read_text())
    add=json.loads((OUT/'registration_addendum.json').read_text())
    spec['hashes']['researchlab\\p27_bab.py']=add['corrected_code_sha256']
    for p,h in spec['hashes'].items():
        if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise ValueError('Frozen file changed')
    if (OUT/'results.json').exists():raise ValueError('Already evaluated')
    dates,y,x=load();sd=y.std(ddof=1)*np.sqrt(12)
    metrics={'monthly_mean':float(y.mean()),'annual_sd':float(sd),'annual_sharpe':float(y.mean()*12/sd),'ff3_monthly_alpha':float(np.linalg.lstsq(x[:,:4],y,rcond=None)[0][0]),'ff4_monthly_alpha':float(np.linalg.lstsq(x,y,rcond=None)[0][0])}
    intervals=[]
    for block in (3,12,24):
        rng=np.random.default_rng(270000+block);means=[];alphas=[]
        for batch in range(100):
            idx=stationary_indices(len(y),100,1/block,rng);xx=x[idx];yy=y[idx]
            b=np.linalg.solve(np.einsum('bni,bnj->bij',xx,xx),np.einsum('bni,bn->bi',xx,yy)[...,None])[...,0]
            means.extend(yy.mean(1)*12);alphas.extend(b[:,0])
        intervals.append({'block_months':block,'paths':10000,'seed':270000+block,'annual_mean_ci95':np.quantile(means,[.025,.975]).tolist(),'ff4_monthly_alpha_ci95':np.quantile(alphas,[.025,.975]).tolist()})
    numerical=all(abs(metrics[k]-v)<=spec['numerical_tolerances'][k] for k,v in spec['targets'].items())
    result={'sample_first':int(dates[0]),'sample_last':int(dates[-1]),'n':len(y),'metrics':metrics,'numerical_gate_pass':numerical,'bootstrap':intervals,'advance_to_execution_audit':bool(numerical and all(z['annual_mean_ci95'][0]>0 and z['ff4_monthly_alpha_ci95'][0]>0 for z in intervals)),'exact_replication':False,'strategy_validated':False,'independent_confirmation':False}
    with (OUT/'results.json').open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps(result,indent=2))
if __name__=='__main__':
    import sys
    register() if '--register' in sys.argv else main()
