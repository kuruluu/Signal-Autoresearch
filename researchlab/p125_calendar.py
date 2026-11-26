"""Fixed P125 calendar effect on dated CRSP aggregate."""
from pathlib import Path
import json,hashlib,datetime
import numpy as np,pandas as pd
from .reality_check import stationary_indices
R=Path(__file__).resolve().parents[1];B=R/'research/replication_first';O=B/'p125_partial_001';D=B/'p24_inputs/author_daily_2021.csv'
def register():
 O.mkdir(exist_ok=True)
 s={'id':'P125_partial_001','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'paper':'French1980 JFE March DOI10.1016/0304-405X(80)90021-5; publisher abstract only, full methods blocked','sample_end':'1977-12','windows':{'original':['1953-01','1977-12'],'post_publication':['1980-04','2020-12']},'construction':'Hypothesis screen, not replication: CRSP aggregate total daily return; Monday weekday versus all other sessions including rare Saturdays. Month paired sums/counts. Native S&P price definition, dividend/holiday exclusions unaudited. No numeric match claim.','gate':'Monday negative and other sessions positive in both periods, all95percent3/12/24month10000stationary bootstrap CIs for Other-Monday positive in both; seeds125000+100*windowindex+block. No alternative weekday/holiday windows.','limits':'Partial abstract-defined mechanism only; no native full methods or S&P series replication, not independent, not executable strategy.','hashes':{str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),R/'researchlab/reality_check.py',D]}}
 with (O/'registration.json').open('x') as f:json.dump(s,f,indent=2)
def calc(a):return a[...,2].sum(-1)/a[...,3].sum(-1)-a[...,0].sum(-1)/a[...,1].sum(-1)
def main():
 s=json.loads((O/'registration.json').read_text())
 for p,h in s['hashes'].items():assert hashlib.sha256((R/p).read_bytes()).hexdigest()==h
 f=pd.read_csv(D,parse_dates=['date']).set_index('date');assert f.index.max().year==2020
 f=f.loc['1926-01':];assert f.vwretd.notna().all();g=f.groupby(f.index.to_period('M'));rows=[]
 for month,z in g:
  assert len(z)>=4
  mask=z.index.dayofweek==0
  v=z.vwretd.to_numpy();rows.append((month,v[mask].sum(),mask.sum(),v[~mask].sum(),(~mask).sum()))
 p=pd.DataFrame([x[1:] for x in rows],index=[x[0] for x in rows]);assert p.index.equals(pd.period_range('1926-01','2020-12',freq='M'));res={}
 for i,(name,(start,end)) in enumerate(s['windows'].items()):
  a=p.loc[start:end].to_numpy();ci=[]
  for b in (3,12,24):
   idx=stationary_indices(len(a),10000,1/b,np.random.default_rng(125000+100*i+b));ci.append({'block':b,'paths':10000,'seed':125000+100*i+b,'difference_ci95':np.quantile(calc(a[idx]),[.025,.975]).tolist()})
  res[name]={'months':len(a),'Mondaymean':float(a[:,0].sum()/a[:,1].sum()),'Othermean':float(a[:,2].sum()/a[:,3].sum()),'difference':float(calc(a)),'bootstrap':ci,'gate':bool(all(z['difference_ci95'][0]>0 for z in ci))}
 numerical=all(v['Mondaymean']<0 and v['Othermean']>0 for v in res.values())
 result={'windows':res,'numerical':numerical,'advance':bool(numerical and res['original']['gate'] and res['post_publication']['gate']),'strategy_validated':False,'independent_confirmation':False}
 with (O/'results.json').open('x') as f:json.dump(result,f,indent=2)
 print(json.dumps(result,indent=2))
if __name__=='__main__':
 import sys
 register() if '--register' in sys.argv else main()
