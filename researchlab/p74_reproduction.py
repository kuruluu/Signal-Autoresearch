"""Registered partial reproduction of P74 Table V Model5-L."""
import argparse,json,io,re
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from .p74_model import filter_model
from .qml_covariance import sandwich
from .p52_reproduction import digest

ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'research/replication_first';OUT=BASE/'p74_partial_001'
SCALE=np.array([.01,5,3,.5,30,.3,.5,.5])
START=np.array([.01,-4,-3,.5,25,-.2,.3,.2])


def register():
    files=[Path(__file__),ROOT/'researchlab/p74_model.py',ROOT/'researchlab/qml_covariance.py',BASE/'p24_inputs/monthly_archive.txt',BASE/'p74_audit/published.pdf']
    spec=dict(id='P74_partial_001',target='Published TableV Model5-L a1=-6.119 robust t=-2.426; nominal monthly log excess return1951Apr-1989Dec',
        deviations=['July2015 French broad-market return instead of original NYSE-only index; revised Ibbotson bill vintage','Initialization original unspecified: fixed fundamental variance.0025 first month; score all465months','Exact original solver/initialization unavailable; declared modern optimizer'],
        transform='Market simple return=Mkt-RF+RF; y=log1p(market)-log1p(RF); bill=log1p(RF); monthly decimal units',
        estimator='Published Model5-L signed-shock recursion with g2=0; joint Gaussian QML; no clipping; initial variance.0025. Seasonal standard-deviation factors squared in variance.',
        solver='Nelder-Mead scaled coordinates, maxiter3500,xatol1e-7,fatol1e-10; two starts0.9 and1.1 times[.01,-4,-3,.5,25,-.2,.3,.2]; scale[.01,5,3,.5,30,.3,.5,.5]; invalid path penalty1e8',
        numerical_gate='Both successful, improve initial objectives, scaled central gradient at1e-5 <=1e-4, objective difference<=1e-6. Failure => numerically inconclusive; no historical retries.',
        inference='Independent-observation robust QML sandwich, summed Hessian/per-observation scores, scaled derivative steps3e-4 and1e-4; require positive information and allSE relative difference<=5%; no inverse-Hessian-only claims',
        numerical_match='Conditional on numerical gate: a1 negative and abs(a1+6.119)<=3.0; a0 within.01 of.01536;g1 within.15 of-.338. Approximate fidelity screen, not equivalence.',
        effect_gate='a1 negative with robust abs(t)>=1.96 at both derivative steps; separate from numerical match; no signal validated by fullsample result',
        other_targets={'b1':.281,'b2':81.002,'lambda_oct':.349,'lambda_jan':.299,'loglik':1279.081},
        units_note='Published b0 scaling label unresolved; fit freely in decimal log-variance units and report without using it as match gate.',
        hashes={str(p.relative_to(ROOT)):digest(p) for p in files})
    OUT.mkdir(exist_ok=True);f=OUT/'registration.json'
    if f.exists():
        old=json.loads(f.read_text());assert {k:v for k,v in old.items() if k!='registered_at_utc'}==spec;return spec
    spec['registered_at_utc']=datetime.now(timezone.utc).isoformat();f.write_text(json.dumps(spec,indent=2));return spec


def run():
    assert (OUT/'registration.json').exists();register();assert not (OUT/'results.json').exists()
    lines=(BASE/'p24_inputs/monthly_archive.txt').read_text().splitlines();rows=[x for x in lines if re.match(r'^\s*\d{6},',x)]
    f=pd.read_csv(io.StringIO('date,Mkt-RF,SMB,HML,RF\n'+'\n'.join(rows)),index_col=0);f.index=pd.PeriodIndex(f.index.astype(str),freq='M');f=f.loc['1951-04':'1989-12']/100
    assert len(f)==465;y=np.log1p(f['Mkt-RF']+f.RF).to_numpy()-np.log1p(f.RF).to_numpy();rf=np.log1p(f.RF).to_numpy();months=f.index.month
    def ll(z):return filter_model(z*SCALE,y,rf,months,.0025)['loglikelihood']
    def objective(z):
        try:return -ll(z).mean()
        except (ValueError,OverflowError):return 1e8
    runs=[]
    for mult in [.9,1.1]:
        start=START/SCALE*mult;fit=minimize(objective,start,method='Nelder-Mead',options={'maxiter':3500,'xatol':1e-7,'fatol':1e-10});z=fit.x;eye=np.eye(8)*1e-5
        grad=np.array([(objective(z+e)-objective(z-e))/(2e-5) for e in eye])
        runs.append(dict(success=bool(fit.success),initial=objective(start),objective=float(fit.fun),parameters=(z*SCALE).tolist(),gradient_max=float(abs(grad).max()),iterations=int(fit.nit)))
        (OUT/'fit_progress.json').write_text(json.dumps(runs,indent=2));print('Completed start',mult,flush=True)
    valid=all(r['success'] and r['objective']<r['initial'] and r['gradient_max']<=1e-4 for r in runs) and abs(runs[0]['objective']-runs[1]['objective'])<=1e-6
    covariance=[];error=None
    if valid:
        z=np.array(runs[0]['parameters'])/SCALE
        try:
            for step in [3e-4,1e-4]:
                c=sandwich(ll,z,step);se=np.sqrt(np.diag(c['covariance']))*SCALE;covariance.append(dict(step=step,se=se.tolist(),condition=c['condition_number']))
        except (ValueError,np.linalg.LinAlgError) as exc:error=str(exc)
    stable=len(covariance)==2 and bool((abs(np.array(covariance[0]['se'])/np.array(covariance[1]['se'])-1)<=.05).all())
    p=np.array(runs[0]['parameters']);match=bool(valid and stable and p[1]<0 and abs(p[1]+6.119)<=3 and abs(p[0]-.01536)<=.01 and abs(p[5]+.338)<=.15)
    effect=bool(valid and stable and p[1]<0 and all(abs(p[1]/c['se'][1])>=1.96 for c in covariance))
    result=dict(runs=runs,numerical_gate=bool(valid),covariance=covariance,covariance_error=error,derivative_stability=stable,partial_match=match,effect_gate=effect,tradable_signal_validated=False)
    (OUT/'results.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');a=p.parse_args()
    if a.run:run()
    else:register();print('Registered; no historical outcomes computed.')
