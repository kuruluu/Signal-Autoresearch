"""P53 literal-lag Dow mechanism, no executable-account claim."""
from pathlib import Path
import json,hashlib,datetime
import numpy as np
import pandas as pd
from .reality_check import stationary_indices
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'research/replication_first';OUT=BASE/'p53_partial_001';DATA=BASE/'p50_audit/DJIA.csv'

def panel(prices):
    rho=np.exp(-1/5);reference=float(prices.iloc[0]);vol=None;rows=[]
    # State at i-1 includes its pricechange in vol, excludes its price in reference.
    for i in range(1,len(prices)-1):
        prev=float(prices.iloc[i-1]);current=float(prices.iloc[i])
        if i>=61:
            if vol is None or vol<=0:raise ValueError('Invalidvol')
            change=float(prices.iloc[i+1])-current
            rows.append((prices.index[i+1],np.sign(prev-reference)*change/vol,change/vol))
        reference=rho*reference+(1-rho)*prev
        delta=abs(current-prev);vol=delta if vol is None else rho*vol+(1-rho)*delta
    return pd.DataFrame([(t,l) for _,t,l in rows],index=[d for d,_,_ in rows],columns=['trend','long'])

def alpha(a):
    y=a[...,0];x=a[...,1];xc=x-x.mean(-1,keepdims=True)
    beta=(xc*(y-y.mean(-1,keepdims=True))).sum(-1)/(xc*xc).sum(-1)
    return y.mean(-1)-beta*x.mean(-1)

def register():
    OUT.mkdir(exist_ok=True)
    spec={'id':'P53_partial_001','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Dowmechanism,notnativeGFD; modernDowfromMay1896; lastcompleteOct2023 (Novsourcepartial). Pastvieweddata,notindependentconfirmation.',
    'timing':'LiteralEq2:atclosei, signal sign(p[i-1]-EMAexcludingp[i-1]), size1/vol[i-1], outcome p[i+1]-p[i]. Deliberateextraone-monthlag, no simultaneousfillclaim. PriceEMA rhoexp(-1/5), initializefirstprice; volEMAabschanges includesi-1,initialfirstabschange. Requirei>=61, nootherdecays.',
    'drift':'OLSintercept trendPnL onidenticallyrisknormalizedlongPnL; sameunits. Paperdriftunitsambiguous, explicitpartialinterpretation, notexactreportedTstar. Fullsampledescriptivefitonly,notentryrule.',
    'windows':{'historical':[190107,201312],'later':[201401,202310]},
    'gate':'Eachwindowmeantrend>0 andOLSintercept>0 plusall3/12/24month10000pairedstationarybootstrap95%interceptlowerbounds>0,seeds530000+100*windowindex+block. NoexactnumericUSpaper target. Passingpermitsfeasibilityauditonly; failstopsbranch,nolag/decayretuning.',
    'limits':'Priceindexexcludesdividends/financing/costs,notCAGR/account/margin. ConditionalfixedPnLbootstrap,notreformingEMApaths. Noorders/rankings. Bothwindowsalreadyused.',
    'hashes':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),ROOT/'researchlab/reality_check.py',DATA]}}
    with (OUT/'registration.json').open('x') as f:json.dump(spec,f,indent=2)

def main():
    s=json.loads((OUT/'registration.json').read_text())
    add=json.loads((OUT/'registration_addendum.json').read_text())
    s['hashes']['researchlab\\p53_trend.py']=add['code_sha256']
    for p,h in s['hashes'].items():
        if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise ValueError('Frozenchanged')
    f=pd.read_csv(DATA,parse_dates=['date']).set_index('date');f=f.loc['1896-05-01':'2023-10-31'];p=f.value.groupby(f.index.to_period('M')).last().loc['1896-05':'2023-10']
    if not p.index.equals(pd.period_range('1896-05','2023-10',freq='M')):raise ValueError('Monthlygap')
    a=panel(p);result={}
    for i,(name,(start,end)) in enumerate(s['windows'].items()):
        labels=a.index.year*100+a.index.month;x=a.loc[(labels>=start)&(labels<=end)].to_numpy();intervals=[]
        for block in (3,12,24):
            idx=stationary_indices(len(x),10000,1/block,np.random.default_rng(530000+i*100+block));ci=np.quantile(alpha(x[idx]),[.025,.975]).tolist();intervals.append({'block':block,'paths':10000,'seed':530000+i*100+block,'alpha_ci95':ci})
        result[name]={'n':len(x),'mean_trend':float(x[:,0].mean()),'monthly_alpha':float(alpha(x)),'bootstrap':intervals,'gate':bool(x[:,0].mean()>0 and alpha(x)>0 and all(z['alpha_ci95'][0]>0 for z in intervals))}
    result={'windows':result,'advance':all(v['gate'] for v in result.values()),'exact_replication':False,'strategy_validated':False}
    with (OUT/'results.json').open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps(result,indent=2))
if __name__=='__main__':
    import sys
    register() if '--register' in sys.argv else main()
