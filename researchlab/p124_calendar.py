"""Fixed P124 calendar effect on dated CRSP aggregate."""
from pathlib import Path
import json,hashlib,datetime
import numpy as np,pandas as pd
from .reality_check import stationary_indices
R=Path(__file__).resolve().parents[1];B=R/'research/replication_first';O=B/'p124_partial_001';D=B/'p24_inputs/author_daily_2021.csv'
def register():
 O.mkdir(exist_ok=True)
 s={'id':'P124_partial_001','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'paper':'BoumanJacobsen2002 AER December DOI10.1257/000282802762024683; working1997','sample_end':'1998-08','windows':{'original':['1970-01','1998-08'],'post_publication':['2003-01','2020-12']},'construction':'US CRSP valueweighted total-return partial transfer, not MSCI nor37countries. Monthly log returns from sum log1p daily vwretd; November-April versus May-October. Bootstrap paired monthly numerators and counts; label and return travel together. No January controls or trading-cost claim.','gate':'Both original and postpublication seasonal differences positive and all3/12/24month10000path95percent lower bounds positive. No windows/months changed after outcome.','limits':'US partial mechanism only; dated2021 teaching vintage; not independent project confirmation; no native numeric match.','hashes':{str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),R/'researchlab/reality_check.py',D]}}
 with (O/'registration.json').open('x') as f:json.dump(s,f,indent=2)
def calc(a):return a[...,0].sum(-1)/a[...,1].sum(-1)-a[...,2].sum(-1)/a[...,3].sum(-1)
def main():
 s=json.loads((O/'registration.json').read_text())
 for p,h in s['hashes'].items():assert hashlib.sha256((R/p).read_bytes()).hexdigest()==h
 f=pd.read_csv(D,parse_dates=['date']).set_index('date');assert f.index.max().year==2020
 f=f.loc['1926-01':];assert f.vwretd.notna().all();g=f.groupby(f.index.to_period('M'));rows=[]
 for month,z in g:
  assert len(z)>=4
  winter=month.month in (11,12,1,2,3,4)
  v=float(np.log1p(z.vwretd.to_numpy()).sum());rows.append((month,v if winter else 0,int(winter),v if not winter else 0,int(not winter)))
 p=pd.DataFrame([x[1:] for x in rows],index=[x[0] for x in rows]);assert p.index.equals(pd.period_range('1926-01','2020-12',freq='M'));res={}
 for i,(name,(start,end)) in enumerate(s['windows'].items()):
  a=p.loc[start:end].to_numpy();ci=[]
  for b in (3,12,24):
   idx=stationary_indices(len(a),10000,1/b,np.random.default_rng(124000+100*i+b));ci.append({'block':b,'paths':10000,'seed':124000+100*i+b,'difference_ci95':np.quantile(calc(a[idx]),[.025,.975]).tolist()})
  res[name]={'months':len(a),'winter_log_mean':float(a[:,0].sum()/a[:,1].sum()),'summer_log_mean':float(a[:,2].sum()/a[:,3].sum()),'difference':float(calc(a)),'bootstrap':ci,'gate':bool(all(z['difference_ci95'][0]>0 for z in ci))}
 result={'windows':res,'advance':bool(all(v['gate'] for v in res.values())),'strategy_validated':False,'independent_confirmation':False,'native_replication':False}
 with (O/'results.json').open('x') as f:json.dump(result,f,indent=2)
 print(json.dumps(result,indent=2))
if __name__=='__main__':
 import sys
 register() if '--register' in sys.argv else main()
