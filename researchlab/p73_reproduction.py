"""Explicitly partial P73 descriptive reproduction; no executable forecasts."""
import argparse
import io
import json
import re
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA
from .p52_reproduction import digest

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'research/replication_first'
INPUT=BASE/'p73_audit'
OUT=BASE/'p73_partial_001'


def realized_variance(returns):
    r=np.asarray(returns,float)
    if not np.isfinite(r).all(): raise ValueError('Nonfinite returns')
    value=float(r@r+2*(r[:-1]@r[1:]))
    if value<=0: raise ValueError('Nonpositive variance; no clipping permitted')
    return value


def back_transform(log_prediction, error_variance):
    return np.exp(log_prediction+.5*error_variance), np.exp(2*log_prediction+2*error_variance)


def weighted_regression(y, x, sigma):
    y=np.asarray(y,float);x=np.asarray(x,float);s=np.asarray(sigma,float)
    if not np.isfinite(x).all() or not np.isfinite(y).all() or (s<=0).any():raise ValueError('Bad regression')
    a=x/s[:,None];b=y/s
    beta=np.linalg.lstsq(a,b,rcond=None)[0];e=b-a@beta
    inv=np.linalg.inv(a.T@a);scores=a*e[:,None]
    hc0=inv@(scores.T@scores)@inv
    meat=scores.T@scores
    for lag in range(1,13):
        cross=scores[lag:].T@scores[:-lag]
        meat+=(1-lag/13)*(cross+cross.T)
    hac=inv@meat@inv
    return dict(n=len(y),coefficient=beta.tolist(),hc0_se=np.sqrt(np.diag(hc0)).tolist(),
                hac12_se=np.sqrt(np.diag(hac)).tolist(),unweighted_residual_sd=float(np.std(y-x@beta,ddof=x.shape[1])))


def load_inputs():
    d=pd.read_fwf(INPUT/'STKDATD.DAT',widths=[8,10,10,10],header=None,names=['date','total','gain','dividend'])
    d.index=pd.to_datetime(d.date.astype(str),format='%Y%m%d')
    early=d.loc['1928-01-04':'1962-07-02','gain']
    raw=json.loads((INPUT/'spx_1962_1984.json').read_text())
    idx=pd.to_datetime(raw['timestamp'],unit='s',utc=True).tz_convert('America/New_York').tz_localize(None).normalize()
    close=pd.Series(raw['indicators']['quote'][0]['close'],index=idx)
    later=close.pct_change(fill_method=None).loc['1962-07-03':'1984-12-31']
    returns=pd.concat([early,later])
    assert returns.index.is_unique and returns.index.is_monotonic_increasing and returns.notna().all()
    assert returns.index.max()<pd.Timestamp('1985-01-01')
    variance=returns.groupby(returns.index.to_period('M')).apply(realized_variance)
    lines=(BASE/'p24_inputs/monthly_archive.txt').read_text().splitlines()
    rows=[line for line in lines if re.match(r'^\s*\d{6},',line)]
    frame=pd.read_csv(io.StringIO('date,Mkt-RF,SMB,HML,RF\n'+'\n'.join(rows)),index_col=0)
    frame.index=pd.PeriodIndex(frame.index.astype(str),freq='M')
    excess=frame['Mkt-RF'].astype(float)/100
    assert len(variance)==684
    return variance,excess.reindex(variance.index)


def register():
    files=[INPUT/'STKDATD.DAT',INPUT/'spx_1962_1984.json',INPUT/'published.pdf',BASE/'p24_inputs/monthly_archive.txt',Path(__file__),ROOT/'researchlab/p52_reproduction.py']
    spec=dict(id='P73_partial_001',target='JFE1987 Table1 fullsample volatility and Table4 PanelA monthly regressions, Feb1928-Dec1984 N683',
        deviations=['Monthly dependent return: July2015 French broad-market Mkt-RF instead of original NYSE-only CRSP less original bill yield',
                    'S&P capital-gain series combines Schwert1990 author data throughJuly2 1962 with Yahoo daily closes thereafter; revised price vintage and rounding',
                    'Exclude Jan3 1928 Dow-composite return; January1928 volatility has only S&P observations fromJan4',
                    'Modern exact state-space Gaussian MA estimation/initialization may differ from original estimator'],
        definition='Within-month sum(r^2)+2sum(adjacent products), no demeaning/cross-month products/clipping. 684 monthly sigma values.',
        forecast='ARIMA(0,0,3) plus constant fit to683 first differences of log sigma, enforce invertibility, statespace maximum likelihood maxiter1000. One-step fitted difference plus prior log sigma. Fullsample parameters intentionally descriptive, not causal trading.',
        correction='MA innovation sigma2; E[sigma]=exp(logprediction+.5sigma2); E[variance]=exp(2logprediction+2sigma2)',
        regressions='Table4 equations6 and7 for both sigma and variance; constant; divide all X and y rows by predicted sigma. HC0 matches White asymptotic estimator, HAC12 additional diagnostic. No selection among four regressions.',
        target_values=dict(sigma_mean=.0474,sigma_sd=.0325,predictable_sigma_beta=.023,predictable_variance_beta=.335,surprise_sigma_gamma=-1.010,surprise_variance_gamma=-4.438),
        gate='Approximate partial numerical reproduction iff sigma mean and sd each within.003, equation6 sigma beta within.15 and variance beta within1.5, equation7 sigma gamma within.25 and variance gamma within1.5; both gammas negative. Tolerances account for altered inputs, not formal equivalence or investment success.',
        inference='Descriptive HC0 and HAC12 condition on generated forecasts; no full-model bootstrap claim. No Monte Carlo trading inference in this stage. Later causal forecast test must be separately registered and account for parameter estimation.',
        promotion='Passing descriptive reproduction never validates a signal. Before ETF work register strictly causal forecast/persistence test; same-month volatility surprises forbidden as earlier predictors.',
        failure='If optimizer fails convergence or variance nonpositive, record problem without tuning specification or clipping.',
        dependencies={'statsmodels':'0.14.6','patsy':'1.0.2','scipy':'1.16.3'},hashes={str(p.relative_to(ROOT)):digest(p) for p in files})
    OUT.mkdir(exist_ok=True);f=OUT/'registration.json'
    if f.exists():
        old=json.loads(f.read_text());assert {k:v for k,v in old.items() if k!='registered_at_utc'}==spec
        return old
    spec['registered_at_utc']=datetime.now(timezone.utc).isoformat();f.write_text(json.dumps(spec,indent=2));return spec


def run():
    assert (OUT/'registration.json').exists();register();assert not (OUT/'results.json').exists()
    variance,excess=load_inputs();sigma=np.sqrt(variance);logs=np.log(sigma)
    changes=logs.diff().dropna()
    model=ARIMA(changes,order=(0,0,3),trend='c',enforce_invertibility=True).fit(method_kwargs={'maxiter':1000})
    if not model.mle_retvals['converged']:raise RuntimeError('Registered estimator did not converge')
    logpred=logs.shift(1).loc[changes.index]+model.fittedvalues
    ps,pv=back_transform(logpred,float(model.params['sigma2']))
    y=excess.loc[changes.index];ones=np.ones(len(y));estimates={}
    for name,pred,actual in [('sigma',ps,sigma.loc[y.index]),('variance',pv,variance.loc[y.index])]:
        estimates[name+'_eq6']=weighted_regression(y,np.column_stack([ones,pred]),ps)
        estimates[name+'_eq7']=weighted_regression(y,np.column_stack([ones,pred,actual-pred]),ps)
    mean=float(sigma.mean());sd=float(sigma.std(ddof=1))
    bs=estimates['sigma_eq6']['coefficient'][1];bv=estimates['variance_eq6']['coefficient'][1]
    gs=estimates['sigma_eq7']['coefficient'][2];gv=estimates['variance_eq7']['coefficient'][2]
    gate=bool(abs(mean-.0474)<=.003 and abs(sd-.0325)<=.003 and abs(bs-.023)<=.15 and abs(bv-.335)<=1.5 and abs(gs+1.010)<=.25 and abs(gv+4.438)<=1.5 and gs<0 and gv<0)
    result=dict(id='P73_partial_001',monthly_sigma_mean=mean,monthly_sigma_sd=sd,
        software_ma_parameters={k:float(v) for k,v in model.params.items()},paper_ma_sign='Paper theta1..3 equals negative software ma.L1..3',
        converged=True,regressions=estimates,partial_numerical_gate=gate,causal_predictive_evidence=False,tradable_signal_validated=False)
    # Keep derived source data local; report only aggregate estimates.
    pd.DataFrame(dict(excess=y,sigma=sigma.loc[y.index],predicted_sigma=ps,predicted_variance=pv)).to_csv(OUT/'monthly_panel.csv')
    (OUT/'results.json').write_text(json.dumps(result,indent=2))
    (OUT/'completion.json').write_text(json.dumps(dict(completed_at_utc=datetime.now(timezone.utc).isoformat(),hashes={p.name:digest(p) for p in OUT.iterdir() if p.is_file()}),indent=2))
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');args=p.parse_args()
    if args.run:run()
    else:register();print('Registered P73; no outcomes computed.')
