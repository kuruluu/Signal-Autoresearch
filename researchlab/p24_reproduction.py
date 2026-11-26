"""Partial reproduction using explicitly mismatched archived daily inputs."""
import argparse
import hashlib
import json
import re
import time
import numpy as np
import pandas as pd
from .catalog import RESEARCH,ROOT
from .experiment import save
from .integrity import sha

INPUTS=RESEARCH/'replication_first'/'p24_inputs'
OUT=RESEARCH/'replication_first'/'p24_partial_001'

def monthly_factors():
    text=(INPUTS/'monthly_archive.txt').read_text(encoding='utf-8')
    rows=[line.split(',') for line in text.splitlines() if re.match(r'^\d{6},',line)]
    f=pd.DataFrame(rows,columns=['month','market','SMB','HML','rf'])
    f.index=pd.PeriodIndex(f.pop('month'),freq='M')
    f=f.astype(float)/100
    if not f.index.is_unique or f.index.max()>=pd.Period('2024-01'):
        raise ValueError('Invalid or sealed monthly data')
    return f

def ols(y,x,hac_lags=0,hc1=True):
    y=np.asarray(y);x=np.column_stack([np.ones(len(y)),x])
    inv=np.linalg.inv(x.T@x);b=inv@x.T@y;e=y-x@b
    score=x*e[:,None];meat=score.T@score
    for lag in range(1,hac_lags+1):
        cross=score[lag:].T@score[:-lag]
        meat+=(1-lag/(hac_lags+1))*(cross+cross.T)
    cov=inv@meat@inv
    if hc1:cov*=len(y)/(len(y)-x.shape[1])
    se=np.sqrt(np.diag(cov))
    return {'alpha_annual_pct':b[0]*1200,'alpha_se_annual_pct':se[0]*1200,
            'alpha_t':b[0]/se[0],'alpha_95_normal':[1200*(b[0]-1.96*se[0]),1200*(b[0]+1.96*se[0])],
            'beta':b[1],'beta_se':se[1],'r_squared':1-e@e/((y-y.mean())@(y-y.mean())),'n':len(y)}

def construct(daily,monthly,ddof=0):
    if daily.index.max()>=pd.Timestamp('2024-01-01'):raise ValueError('Sealed daily data')
    d=daily.loc['1926-07-01':'2015-04-30']
    if d.isna().any().any():raise ValueError('Missing daily input in target window')
    excess=d.vwretd-d.rf
    rv=excess.groupby(excess.index.to_period('M')).var(ddof=ddof)
    f=monthly.market.loc['1926-08':'2015-04']
    lag=rv.shift(1).reindex(f.index)
    if lag.isna().any() or (lag<=0).any():raise ValueError('Missing/nonpositive lagged variance')
    unscaled=f/lag
    c=f.std(ddof=1)/unscaled.std(ddof=1)
    return pd.DataFrame({'factor':f,'lagged_realized_variance':lag,'weight':c/lag,'managed':unscaled*c}),c

def register():
    OUT.mkdir(parents=True,exist_ok=True)
    spec={
      'id':'p24_partial_001','stage':'partial_paper_reproduction','paper':'10.1111/jofi.12513',
      'source':'research/fulltext/P24.pdf, PDF page 9, Table I Panel A column Mkt; equations 1-3 on pages 6-7',
      'target':{'alpha_annual_pct':4.86,'alpha_se_annual_pct':1.56,'beta':.61,'beta_se':.05,'r_squared':.37,'n':1065},
      'sample':'August 1926 through April 2015; exact endpoint inferred from 1065 observations starting after July 1926 variance. Not independently certified from author replication code.',
      'data':'Monthly French July-2015 archive; daily CRSP vwretd minus French RF in author teaching snapshot from April 2021, ending December 2020. Not the original daily FF market-factor vintage.',
      'estimator':'Monthly factor excess return divided by prior calendar-month daily excess-return variance (population denominator). Full-target-sample standard-deviation normalization for descriptive reproduction only. OLS managed excess return on original factor and constant.',
      'inference':'HC1 primary, HC0 and Bartlett Newey-West six monthly lags sensitivity. Paper states heteroskedasticity adjustment but not exact finite-sample variant.',
      'primary_endpoint':'Annualized alpha; beta, SE, R-squared and N are replication diagnostics, not independent discoveries.',
      'fixed_sensitivities':['ddof1 daily variance with HC1','ddof0 with HC0','ddof0 with HAC6'],
      'decision':'At best partial reproduction: known data mismatch precludes exact. Numerically close if N=1065, alpha within 0.50 pp/year, beta within .05, alpha SE within .25 pp/year and R2 within .05. These are descriptive approximation tolerances, not equivalence tests. Otherwise mark inconclusive discrepancy unless audited exact inputs support inconsistency.',
      'tolerance_reason':'Approximately 10% of reported alpha, 8% of beta and 16% of alpha SE; fixed practical diagnostics for known data differences, not rounding tolerances.',
      'power_note':'Normal 80%-power two-sided alpha MDE approximated by (1.96+.84)*robust SE; descriptive precision only, data-dependent.',
      'tradeability':'No fees, leverage limits or causal scaling normalization. No economic signal verdict or fresh confirmation.',
      'inputs':{str(p.relative_to(ROOT)):sha(p) for p in [INPUTS/'author_daily_2021.csv',INPUTS/'monthly_archive.txt',RESEARCH/'fulltext/P24.pdf']},
      'code_sha256':sha(ROOT/'researchlab/p24_reproduction.py'),'final_access':False}
    path=OUT/'registration.json'
    if path.exists():
        old=json.loads(path.read_text())['spec']
        if old!=spec:
            amendment=OUT/'reporting_amendment.json'
            a=json.loads(amendment.read_text()) if amendment.exists() else {}
            unchanged={k:v for k,v in old.items() if k!='code_sha256'}=={k:v for k,v in spec.items() if k!='code_sha256'}
            if not (unchanged and a.get('original_code_sha256')==old['code_sha256'] and a.get('updated_code_sha256')==spec['code_sha256']):
                raise ValueError('Registration changed; new version required')
    else:save(path,{'registered_before_run_unix':time.time(),'spec':spec})
    return spec

def run():
    spec=register()
    daily=pd.read_csv(INPUTS/'author_daily_2021.csv',index_col='date',parse_dates=True)
    monthly=monthly_factors()
    data,c=construct(daily,monthly)
    data.to_csv(OUT/'monthly_reproduction.csv')
    result=ols(data.managed,data.factor)
    secondary,c1=construct(daily,monthly,ddof=1)
    sensitivity={'variance_ddof1_HC1':ols(secondary.managed,secondary.factor),
                 'variance_ddof0_HC0':ols(data.managed,data.factor,hc1=False),
                 'variance_ddof0_HAC6':ols(data.managed,data.factor,hac_lags=6)}
    thresholds={'alpha_annual_pct':.50,'beta':.05,'alpha_se_annual_pct':.25,'r_squared':.05,'n':0}
    checks={k:abs(result[k]-spec['target'][k])<=v for k,v in thresholds.items()}
    result.update(normalization_c=c,mean_weight=data.weight.mean(),max_weight=data.weight.max(),
        min_weight=data.weight.min(),approx_alpha_mde_80pct=result['alpha_se_annual_pct']*2.8,
        approximation_checks=checks,
        verdict='Partial reproduction: numerically close, exact replication blocked by data/spec differences' if all(checks.values()) else 'Inconclusive numerical discrepancy with known input/specification differences',
        exact_replication=False,tradable_signal_validated=False)
    save(OUT/'result.json',result);save(OUT/'sensitivity.json',sensitivity)
    save(OUT/'completion.json',{'completed':True,'final_used':False,'primary_claims':1,'secondary_diagnostics':3})
    print((OUT/'result.json').read_text())

if __name__=='__main__':run()
