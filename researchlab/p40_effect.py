"""Registered single-feature P40 contemporary mechanism test."""
import json
import numpy as np
import pandas as pd
from .p40_sessions import OUT


def slope(x,y):
    xc=x-x.mean(axis=-1,keepdims=True)
    yc=y-y.mean(axis=-1,keepdims=True)
    return (xc*yc).sum(axis=-1)/(xc*xc).sum(axis=-1)


def forecast(x,y,dates):
    predictions=[];means=[];actual=[]
    for i,date in enumerate(dates):
        if date<'2021-01-01':continue
        b=slope(x[:i],y[:i]);a=y[:i].mean()-b*x[:i].mean()
        predictions.append(a+b*x[i]);means.append(y[:i].mean());actual.append(y[i])
    actual=np.array(actual)
    model=float(np.mean((actual-predictions)**2))
    baseline=float(np.mean((actual-means)**2))
    return {'n':len(actual),'model_mse':model,'historical_mean_mse':baseline,
            'mse_improvement':1-model/baseline}


def main():
    quality=json.loads((OUT/'quality_summary.json').read_text())
    if not quality['quality_gate']:raise ValueError('Registered data-quality gate failed')
    frame=pd.read_csv(OUT/'features.csv')
    x=frame.first_half_return.to_numpy();y=frame.last_half_return.to_numpy();n=len(x)
    observed=float(slope(x,y));intervals=[]
    for block in (5,20,60):
        rng=np.random.default_rng(40000+block)
        indices=np.empty((5000,n),dtype=np.int32)
        indices[:,0]=rng.integers(n,size=5000)
        for j in range(1,n):
            restart=rng.random(5000)<1/block
            indices[:,j]=np.where(restart,rng.integers(n,size=5000),(indices[:,j-1]+1)%n)
        slopes=slope(x[indices],y[indices])
        intervals.append({'block':block,'paths':5000,'seed':40000+block,
                          'ci95':np.quantile(slopes,[.025,.975]).tolist()})
    recursive=forecast(x,y,frame.date.to_numpy())
    passed=observed>0 and all(r['ci95'][0]>0 for r in intervals) and recursive['mse_improvement']>0
    result={'type':'Contemporary mechanism test; not original paper replication',
            'n':n,'descriptive_full_sample_slope':observed,'bootstrap':intervals,
            'recursive_2021_2023':recursive,'mechanism_gate_pass':bool(passed),
            'independent_confirmation':False,'trading_strategy_validated':False}
    (OUT/'results.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
