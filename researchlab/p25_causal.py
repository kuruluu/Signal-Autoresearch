"""P25 equations15-18 native MOM partial causal allocation reconstruction."""
import json,hashlib
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
from .p25_reconstruction import ROOT,BASE,parse,assemble,sharpe
from .reality_check import stationary_indices

OUT=BASE/'p25_causal_001'


def allocate(original,variance,initial=120):
    original=np.asarray(original);variance=np.asarray(variance)
    raw=original/variance;rows=[]
    for i in range(initial,len(original)):
        prior=original[:i];scaled=raw[:i]
        c=prior.std(ddof=1)/scaled.std(ddof=1)
        training=np.column_stack([c*scaled,prior]);cov=np.cov(training,rowvar=False,ddof=1)
        weights=np.linalg.solve(cov,training.mean(0))/5
        exposure=float(np.clip(weights[0]*c/variance[i]+weights[1],-5,5))
        control=float(np.clip(prior.mean()/(5*prior.var(ddof=1)),-5,5))
        rows.append([exposure*original[i],control*original[i],exposure,control,c])
    return np.array(rows)


def cer(x):return 12*(x.mean(axis=-1)-2.5*x.var(axis=-1,ddof=1))


def register():
    OUT.mkdir(exist_ok=True)
    paths=[Path(__file__),ROOT/'researchlab/p25_reconstruction.py',BASE/'p25_audit/published.pdf',
           BASE/'p08_audit/F-F_Momentum_Factor.CSV',BASE/'p08_audit/F-F_Momentum_Factor_daily.CSV']
    spec={'id':'P25_causal_001','registered_utc':datetime.now(timezone.utc).isoformat(),
          'target':'Table5 PanelA MOM: combinationSR.92,controlSR.49; CER8.47%/2.29%; rounded differences.44/6.18pp',
          'sample':'Jan1927-Dec2016 inputs; initial120months; Jan1937-Dec2016 scoring N960, alreadyvieweddevelopment',
          'rules':'Eq15 training-only c_t equalizes sample variance; expanding mean/covariance of [c_t*f/lagvariance,f], unconstrained mean-variance weights inv(cov)*mean/gamma5. Eq16 collapse underlying exposure then clip[-5,5]. Control prior-only mean/(5*samplevariance),clip[-5,5]. Current return never included in estimates. No cov regularization/pseudoinverse/fallback; numerical failures block rather than impute.',
          'metrics':'AnnualSRsqrt12*mean/sampleSD; annual excessCER12*(mean-5/2*samplevariance); no RF added to excess-return CER. Not accountCAGR or costs.',
          'numerical_gate':'Both SR within.08 of targets and bothCERwithin1pp; report every deviation. No parameter tuning.',
          'inference':'Paired fixed causal excess return rows,10000stationary paths,monthlyblocks3/12/24,seeds25503/25512/25524; CI for annualSR difference and annualCERgain. Fixedstreams not synthetic-history retraining.',
          'advance':'Numerical gate plus both gain95%CIlower>0 allblocks permit feasibility audit of executable momentum instrument. No strategyranking/order without capital,borrow,costs,availability and independentconfirmation.',
          'limits':'Native factor exposurecap5 not permission for broker5xleveraging. Originalfactor stock-universe/borrow/turnover not10kaccount. 2020data revision differs nativevintage. Onlyonefactor,not103strategyconclusion.',
          'hashes':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},'sealed':'No2024-2025observations'}
    with (OUT/'registration.json').open('x') as f:json.dump(spec,f,indent=2)


def main():
    spec=json.loads((OUT/'registration.json').read_text())
    for name,digest in spec['hashes'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest
    assert not (OUT/'results.json').exists()
    folder=BASE/'p08_audit';frame,_=assemble(parse(folder/'F-F_Momentum_Factor_daily.CSV',True),parse(folder/'F-F_Momentum_Factor.CSV',False))
    rows=allocate(frame.original,frame.lag_variance);returns=rows[:,:2].T
    sr=sharpe(returns);ce=cer(returns);intervals=[]
    for block in (3,12,24):
        rng=np.random.default_rng(25500+block);ds=[];dc=[]
        for offset in range(0,10000,100):
            idx=stationary_indices(len(rows),100,1/block,rng)
            sampled=rows[idx,:2].transpose(0,2,1)
            s=sharpe(sampled);c=cer(sampled)
            ds.extend(s[:,0]-s[:,1]);dc.extend(c[:,0]-c[:,1])
        intervals.append({'block_months':block,'paths':10000,'seed':25500+block,
                          'sharpe_gain_ci95':np.quantile(ds,[.025,.975]).tolist(),
                          'cer_gain_ci95_percent':(100*np.quantile(dc,[.025,.975])).tolist()})
    numerical=bool((np.abs(sr-[.92,.49])<=.08).all() and (np.abs(100*ce-[8.47,2.29])<=1).all())
    result={'type':'P25 Table5 MOM causal native-factor partial reconstruction; not executable account',
            'n_months':len(rows),'sharpe_combination_control':sr.tolist(),'cer_percent_combination_control':(100*ce).tolist(),
            'sharpe_gain':float(sr[0]-sr[1]),'cer_gain_pp':float(100*(ce[0]-ce[1])),
            'numerical_gate_pass':numerical,'bootstrap':intervals,
            'advance_to_execution_feasibility':numerical and all(r['sharpe_gain_ci95'][0]>0 and r['cer_gain_ci95_percent'][0]>0 for r in intervals),
            'exposure_min_max':rows[:,2].min().item(), 'exposure_max':rows[:,2].max().item(),
            'independent_confirmation':False,'trading_strategy_validated':False}
    (OUT/'results.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))


if __name__=='__main__':
    import sys
    register() if '--register' in sys.argv else main()
