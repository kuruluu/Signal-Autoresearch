"""Registered development test of P73's causal monthly forecasting route."""
import argparse
import json
import warnings
from datetime import datetime, timezone
import numpy as np
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA
from .p73_reproduction import ROOT, BASE, load_inputs, back_transform
from .p52_reproduction import digest, holm

OUT=BASE/'p73_causal_001'


def fit_volatility(history):
    logs=np.log(np.sqrt(np.asarray(history,float)))
    with warnings.catch_warnings(record=True) as caught:
        fit=ARIMA(np.diff(logs),order=(0,0,3),trend='c',enforce_invertibility=True).fit(method_kwargs={'maxiter':1000})
    if not fit.mle_retvals['converged']:
        return np.nan,np.nan,'nonconvergence'
    innovation_variance=float(dict(zip(fit.param_names,fit.params))['sigma2'])
    s,v=back_transform(logs[-1]+float(fit.forecast(1)[0]),innovation_variance)
    if not np.isfinite([s,v]).all() or min(s,v)<=0:return np.nan,np.nan,'invalid_prediction'
    return float(s),float(v),'; '.join(sorted(set(type(w.message).__name__ for w in caught)))


def rolling_volatility(variance,window=60,forecaster=fit_volatility,progress=None):
    rows=[]
    for i in range(window,len(variance)):
        try:s,v,status=forecaster(variance.iloc[i-window:i])
        except (ValueError,np.linalg.LinAlgError) as exc:s,v,status=np.nan,np.nan,type(exc).__name__
        rows.append((variance.index[i],s,v,status))
        if progress and (i-window+1)%50==0:progress(i-window+1,len(variance)-window)
    return pd.DataFrame(rows,columns=['month','predicted_sigma','predicted_variance','status']).set_index('month')


def return_forecasts(features,excess,window=60):
    rows=[]
    for i in range(window,len(features)):
        month=features.index[i]; prior=features.iloc[i-window:i]; y=excess.reindex(prior.index).to_numpy()
        mean=float(y.mean());valid=prior[['predicted_sigma','predicted_variance']].notna().all().all() and features.iloc[i][['predicted_sigma','predicted_variance']].notna().all()
        if valid:
            s=prior.predicted_sigma.to_numpy();v=prior.predicted_variance.to_numpy()
            x=np.column_stack([np.ones(window),v]);beta=np.linalg.lstsq(x/s[:,None],y/s,rcond=None)[0]
            pred=float(beta@[1,features.iloc[i].predicted_variance]);weighted_mean=float(np.average(y,weights=1/s**2))
            slope=float(beta[1])
        else:
            pred=weighted_mean=mean;slope=np.nan
        rows.append((month,float(excess.loc[month]),pred,mean,weighted_mean,slope,bool(valid)))
    return pd.DataFrame(rows,columns=['month','actual','forecast','mean_control','weighted_mean_control','slope','model_used']).set_index('month')


def block_test(loss_differences,block,paths=5000):
    values=np.asarray(loss_differences,float);n,k=values.shape;rng=np.random.default_rng(73101+block);draws=np.empty((paths,k))
    for offset in range(0,paths,100):
        count=min(100,paths-offset);idx=np.empty((count,n),int);idx[:,0]=rng.integers(n,size=count)
        for j in range(1,n):idx[:,j]=np.where(rng.random(count)<1/block,rng.integers(n,size=count),(idx[:,j-1]+1)%n)
        draws[offset:offset+count]=values[idx].mean(1)
    mean=values.mean(0);p=(1+(np.abs(draws-mean)>=np.abs(mean)).sum(0))/(paths+1)
    return dict(block_months=block,paths=paths,ci95=np.quantile(draws,[.025,.975],axis=0).T.tolist(),
        centered_two_sided_p=p.tolist(),holm_p=holm(p).tolist(),p_mc_se=np.sqrt(p*(1-p)/(paths+1)).tolist())


def register():
    files=[ROOT/'researchlab/p73_reproduction.py',ROOT/'researchlab/p52_reproduction.py',ROOT/'researchlab/p73_causal.py',
           BASE/'p73_audit/STKDATD.DAT',BASE/'p73_audit/spx_1962_1984.json',BASE/'p24_inputs/monthly_archive.txt']
    spec=dict(id='P73_causal_001',role='Development test of monthly forecasting mechanism, not literal paper-table replication or fresh holdout',
        window=60,volatility='For each monthJan1933-Dec1984 fit MA3+constant to59 changes in60 PRIOR log monthly sigma values. Same estimator as partial reproduction. One-step mean with past innovation-variance lognormal correction.',
        return_model='For each monthJan1938-Dec1984 fit WLS excess return=constant+predicted variance to previous60 causal forecast/realized-return pairs, row scaling1/predicted_sigma. Predict current month using its causal forecast. No current returns or realized volatility in predictors. No coefficient sign restriction, clipping or model selection.',
        comparators=['Prior60month arithmetic mean excess return','Prior60month WLS constant using identical forecast volatility weights'],
        expected_evaluation_months=564,primary='Mean squared-error reduction against BOTH controls; minimum1% relative reduction for each',
        gate='At least95% model-used coverage, relative MSE improvement>=.01 versus both controls, positive marginal95CI and Holm2 p<=.05 for both paired loss differences at all block lengths6/12/24',
        fallback='If MA fails convergence/finite-positive prediction, record missing. If current or any previous60 forecast unavailable, all return forecasts use simple mean; observations remain scored. No retry/retuning. Coverage gate prevents fallback masquerading as success.',
        monte_carlo='5000 common stationary monthly resamples of two realized paired squared-loss difference series, seed73101+block; repeat20000 if any Holm p in[.04,.06]. Conditions on recursively produced forecast/loss path; does NOT refit whole learning algorithm or reproduce estimation uncertainty across hypothetical histories. Model refitted60months at every actual decision.',
        limits=['Same1928-1984 source already inspected: causal timing does not make it untouched','Monthly mechanism does not match desired days-long holding yet','Broad-market dependent series differs from originalNYSE, and original daily GARCH-in-mean route remains untested','No costs,ETF fill or investment utility claim; predictive gate is research screen only'],
        promotion='Pass is permission for additional research, not trade approval. Failure sets aside this monthly route without retuning; do not reverse coefficient or use surprise regressors.',
        hashes={str(p.relative_to(ROOT)):digest(p) for p in files})
    OUT.mkdir(exist_ok=True);f=OUT/'registration.json'
    if f.exists():
        old=json.loads(f.read_text());assert {k:v for k,v in old.items() if k!='registered_at_utc'}==spec;return old
    spec['registered_at_utc']=datetime.now(timezone.utc).isoformat();f.write_text(json.dumps(spec,indent=2));return spec


def run():
    assert (OUT/'registration.json').exists();spec=register();assert not (OUT/'results.json').exists()
    variance,excess=load_inputs()
    def progress(done,total):
        (OUT/'progress.json').write_text(json.dumps(dict(forecasts_done=done,total=total,updated_at_utc=datetime.now(timezone.utc).isoformat())))
        print(f'Volatility forecasts {done}/{total}',flush=True)
    features=rolling_volatility(variance,progress=progress);features.to_csv(OUT/'volatility_forecasts.csv')
    panel=return_forecasts(features,excess);assert len(panel)==564
    panel.to_csv(OUT/'return_forecasts.csv');model_loss=(panel.actual-panel.forecast)**2
    control_losses=np.column_stack([(panel.actual-panel[c])**2 for c in ['mean_control','weighted_mean_control']])
    differences=control_losses-model_loss.to_numpy()[:,None];relative=1-model_loss.mean()/control_losses.mean(0)
    inference=[block_test(differences,b) for b in [6,12,24]]
    if any(.04<=p<=.06 for b in inference for p in b['holm_p']):inference=[block_test(differences,b,20000) for b in [6,12,24]]
    coverage=float(panel.model_used.mean());passes=bool(coverage>=.95 and (relative>=.01).all() and all((np.array(b['ci95'])[:,0]>0).all() and (np.array(b['holm_p'])<=.05).all() for b in inference))
    result=dict(id=spec['id'],sample=[str(panel.index[0]),str(panel.index[-1])],months=len(panel),coverage=coverage,
        volatility_missing=int(features.predicted_variance.isna().sum()),model_mse=float(model_loss.mean()),control_mse=control_losses.mean(0).tolist(),
        relative_mse_improvement=relative.tolist(),mean_loss_differences=differences.mean(0).tolist(),bootstrap=inference,predictive_gate=passes,
        tradable_signal_validated=False,limitations=spec['limits'],uncertainty_scope=spec['monte_carlo'])
    (OUT/'results.json').write_text(json.dumps(result,indent=2))
    (OUT/'completion.json').write_text(json.dumps(dict(completed_at_utc=datetime.now(timezone.utc).isoformat(),hashes={p.name:digest(p) for p in OUT.iterdir() if p.is_file()}),indent=2))
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');args=p.parse_args()
    if args.run:run()
    else:register();print('Registered P73 causal test; no outcomes computed.')
