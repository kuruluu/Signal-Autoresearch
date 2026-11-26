"""One fixed P25 MOM table reconstruction; ex-post scale is descriptive only."""
import json,re,hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from .reality_check import stationary_indices

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'research/replication_first';OUT=BASE/'p25_partial_001'


def parse(path,daily):
    digits=8 if daily else 6;rows=[]
    for line in path.read_text().splitlines():
        match=re.match(r'^\s*(\d{'+str(digits)+r'}),\s*(-?[\d.]+)\s*$',line)
        if match:
            date,value=match.groups();number=float(value)
            if number in (-99.99,-999):raise ValueError('Missing factor value')
            rows.append((pd.to_datetime(date,format='%Y%m%d' if daily else '%Y%m'),number/100))
    result=pd.Series(dict(rows)).sort_index()
    if len(result)!=len(rows):raise ValueError('Duplicate factor dates')
    if not daily:result.index=result.index.to_period('M')
    return result


def assemble(daily,monthly,start='1927-01',end='2016-12'):
    variance=daily.pow(2).groupby(daily.index.to_period('M')).mean()*22
    variance.index=variance.index+1
    expected=pd.period_range(start,end,freq='M')
    frame=pd.DataFrame({'original':monthly,'lag_variance':variance}).reindex(expected)
    if frame.isna().any().any() or (frame.lag_variance<=0).any():raise ValueError('Missing/invalid target months; no imputation')
    unscaled=frame.original/frame.lag_variance
    scale=frame.original.std(ddof=1)/unscaled.std(ddof=1)
    frame['managed']=scale*unscaled
    return frame,float(scale)


def sharpe(x):return np.sqrt(12)*x.mean(axis=-1)/x.std(axis=-1,ddof=1)


def main():
    spec=json.loads((OUT/'registration.json').read_text())
    for name,digest in spec['hashes'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest
    freeze=json.loads((OUT/'analysis_freeze.json').read_text());assert freeze['code_sha256']==hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    assert not (OUT/'results.json').exists()
    folder=BASE/'p08_audit'
    frame,scale=assemble(parse(folder/'F-F_Momentum_Factor_daily.CSV',True),parse(folder/'F-F_Momentum_Factor.CSV',False))
    a=frame[['original','managed']].to_numpy().T
    sr=sharpe(a);means=12*a.mean(axis=1)*100;sd=np.sqrt(12)*a.std(axis=1,ddof=1)*100
    corr=float(np.corrcoef(a)[0,1]);intervals=[]
    for block in (3,12,24):
        rng=np.random.default_rng(25300+block);draws=[]
        for offset in range(0,10000,100):
            idx=stationary_indices(len(frame),100,1/block,rng)
            samples=a[:,idx].transpose(1,0,2);ratios=sharpe(samples)
            draws.extend(ratios[:,1]-ratios[:,0])
        intervals.append({'block_months':block,'paths':10000,'seed':25300+block,'sharpe_difference_ci95':np.quantile(draws,[.025,.975]).tolist()})
    numerical=abs(means[0]-7.94)<=.5 and abs(sd[0]-16.39)<=.5 and abs(means[1]-16.17)<=1 and abs((sr[1]-sr[0])-.50)<=.08 and abs(corr-.48)<=.05
    result={'type':'P25 Table1 MOM partial native-factor reconstruction; ex-post normalized',
            'n_months':len(frame),'scale':scale,'annual_mean_percent':means.tolist(),'annual_sd_percent':sd.tolist(),
            'sharpe_original_managed':sr.tolist(),'sharpe_difference':float(sr[1]-sr[0]),'correlation':corr,
            'numerical_gate_pass':bool(numerical),'bootstrap':intervals,
            'advance_to_causal_methods_audit':bool(numerical and all(r['sharpe_difference_ci95'][0]>0 for r in intervals)),
            'independent_confirmation':False,'trading_strategy_validated':False}
    (OUT/'results.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))


if __name__=='__main__':main()
