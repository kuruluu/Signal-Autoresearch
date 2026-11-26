"""P74 lagged-bill causal development forecast experiment."""
import argparse,io,json,re
from datetime import datetime,timezone
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from .p74_reproduction import ROOT,BASE,SCALE,START
from .p74_model import filter_model
from .p74_forecast import forecast
from .p73_causal import block_test
from .p52_reproduction import digest

OUT=BASE/'p74_causal_001'


def estimate(y,bill,months):
    def objective(z):
        try:return -filter_model(z*SCALE,y,bill,months,.0025)['loglikelihood'].mean()
        except (ValueError,OverflowError):return 1e8
    runs=[]
    for mult in [.9,1.1]:
        start=START/SCALE*mult
        fit=minimize(objective,start,method='Nelder-Mead',options={'maxiter':3500,'xatol':1e-7,'fatol':1e-10})
        z=fit.x;eye=np.eye(8)*1e-5;gradient=max(abs((objective(z+e)-objective(z-e))/2e-5) for e in eye)
        runs.append(dict(success=bool(fit.success),objective=float(fit.fun),initial=objective(start),gradient=float(gradient),parameters=(z*SCALE).tolist()))
    valid=all(r['success'] and r['objective']<r['initial'] and r['gradient']<=1e-4 for r in runs) and abs(runs[0]['objective']-runs[1]['objective'])<=1e-6
    return (np.array(runs[0]['parameters']) if valid else None),runs


def register():
    paths=[ROOT/'researchlab'/n for n in ['p74_causal.py','p74_forecast.py','p74_model.py','p74_reproduction.py','p73_causal.py','p52_reproduction.py']]+[BASE/'p24_inputs/monthly_archive.txt']
    spec=dict(id='P74_causal_001',sample='1994Jan-2014Dec,252months, development already viewed',
        training='Each December fit prior240months, initialvariance.0025; two fixed starts and solver/numerical gates identical to partial reproduction. Refit annually, freeze parameters for12months. Refilter from fixed training start as completed months accumulate.',
        timing='Every training and forecasting conditional variance uses previous completed calendar month logRF, never currentRF. Forecast nextmonth using completed returns only. Revised archival data not point-in-time vintages.',
        controls=['Mean excess log return over previous240completed months','Constant fitted with inverse conditional-variance weights from same annual model and240training observations; frozen next12months'],
        fallback='Failed annual numerical gate: both model and weighted control use current rolling240mean for all12months. Invalid individual forecast uses same fallback; retain and score every month. Coverage>=95% required.',
        objective='Both paired squared-error reductions>=1% relative controlMSE; both marginal95CI positive and Holm2 p<=.05 at blocks6/12/24. At least95% model coverage. No coefficient sign restriction or clipping.',
        uncertainty='5000 joint stationary resamples of realized paired monthly loss differences using p73_causal.block_test; escalate20000 if Holm p in[.04,.06]. Conditional on actual learning path, not complete hypothetical-history refitting.',
        interpretation='Forecast research screen only; neither ETF execution nor economic utility. Lagged-bill adaptation differs from original. Failure preserved without changing optimizer/window/threshold.',
        hashes={str(p.relative_to(ROOT)):digest(p) for p in paths})
    OUT.mkdir(exist_ok=True);f=OUT/'registration.json'
    if f.exists():
        old=json.loads(f.read_text());assert {k:v for k,v in old.items() if k!='registered_at_utc'}==spec;return spec
    spec['registered_at_utc']=datetime.now(timezone.utc).isoformat();f.write_text(json.dumps(spec,indent=2));return spec


def run():
    assert (OUT/'registration.json').exists();register();assert not (OUT/'results.json').exists()
    lines=(BASE/'p24_inputs/monthly_archive.txt').read_text().splitlines();rows=[s for s in lines if re.match(r'^\s*\d{6},',s)]
    f=pd.read_csv(io.StringIO('date,Mkt-RF,SMB,HML,RF\n'+'\n'.join(rows)),index_col=0)/100;f.index=pd.PeriodIndex(f.index.astype(str),freq='M')
    bill=np.log1p(f.RF);y=np.log1p(f['Mkt-RF']+f.RF)-bill
    records=[];fits=[]
    for year in range(1994,2015):
        first=f.index.get_loc(pd.Period(f'{year}-01'));start=first-240
        params,runs=estimate(y.iloc[start:first].to_numpy(),bill.iloc[start-1:first-1].to_numpy(),f.index[start:first].month)
        weighted=None
        if params is not None:
            fit=filter_model(params,y.iloc[start:first],bill.iloc[start-1:first-1],f.index[start:first].month,.0025)
            weighted=float(np.average(y.iloc[start:first],weights=1/fit['variance']))
        fits.append(dict(year=year,valid=params is not None,runs=runs));(OUT/'fit_progress.json').write_text(json.dumps(fits,indent=2))
        for i in range(first,first+12):
            mean=float(y.iloc[i-240:i].mean());pred=control=mean;used=False
            if params is not None:
                try:
                    pred,_=forecast(params,y.iloc[start:i],bill.iloc[start-1:i],f.index[start:i].month,f.index[i].month)
                    control=weighted;used=True
                except (ValueError,OverflowError):pass
            records.append(dict(month=str(f.index[i]),actual=float(y.iloc[i]),forecast=pred,mean=mean,weighted=control,used=used))
        print('Completed year',year,flush=True)
    panel=pd.DataFrame(records);panel.to_csv(OUT/'forecasts.csv',index=False)
    loss=(panel.actual-panel.forecast)**2;controls=np.column_stack([(panel.actual-panel[c])**2 for c in ['mean','weighted']]);delta=controls-loss.to_numpy()[:,None];relative=1-loss.mean()/controls.mean(0)
    inference=[block_test(delta,b) for b in [6,12,24]]
    if any(.04<=p<=.06 for b in inference for p in b['holm_p']):inference=[block_test(delta,b,20000) for b in [6,12,24]]
    gate=bool(panel.used.mean()>=.95 and (relative>=.01).all() and all((np.array(b['ci95'])[:,0]>0).all() and (np.array(b['holm_p'])<=.05).all() for b in inference))
    result=dict(months=len(panel),coverage=float(panel.used.mean()),relative_mse_improvement=relative.tolist(),bootstrap=inference,predictive_gate=gate,tradable_signal_validated=False)
    (OUT/'results.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');a=p.parse_args()
    if a.run:run()
    else:register();print('Registered; no forecast outcomes computed.')
