"""P02 external sort mechanism, distinct from original daily construction."""
from pathlib import Path
import json,hashlib,datetime
import pandas as pd,numpy as np
from .reality_check import stationary_indices
R=Path(__file__).resolve().parents[1];B=R/'research/replication_first';O=B/'p02_liquid_001';D=B/'p63_archive/liquid.parquet'
def register():
 O.mkdir(exist_ok=True)
 s={'id':'P02_external_001','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Fixed NYSE20percent market-cap screen, not a direct spread/impact measure. External Mom6m EW deciles: five lagged returns at signal month, missing returns zero, then portfolio lag one month; quarterly March/June/September/December signal updates from June start. Not overlapping native six/six, no exact numerical match claim. Chosen from paper six-month emphasis before outcomes, not best-performing twelve-month specification.',
 'windows':{'original':['1965-01','1989-12'],'later':['1993-04','2022-12']},'gate':'Positiveannualarithmeticmean andall95%lowerbounds>0 at3/12/24month10000stationarypaths,seeds21000+windowindex100+block,bothwindows. Noalpha/CAGR/accountclaim. Percentdivide100,zero-investmentnoRFsubtraction. Noothersignal/endpointsearch. Passonlyexecutionaudit.',
 'hashes':{str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),D,R/'researchlab/reality_check.py']}}
 with (O/'registration.json').open('x') as f:json.dump(s,f,indent=2)
def main():
 s=json.loads((O/'registration.json').read_text())
 for p,h in s['hashes'].items():assert hashlib.sha256((R/p).read_bytes()).hexdigest()==h
 f=pd.read_parquet(D,filters=[('signalname','==','Mom6m'),('port','==','LS')]);assert pd.to_datetime(f.date).max().year==2022;f=f.rename(columns={'ret':'Mom6m'});f.index=pd.to_datetime(f.date).dt.to_period('M');f=f.sort_index();res={}
 for i,(name,(start,end)) in enumerate(s['windows'].items()):
  z=f.loc[start:end];assert z.index.equals(pd.period_range(start,end,freq='M')) and z.Mom6m.notna().all();x=z.Mom6m.to_numpy()/100;intervals=[]
  for block in (3,12,24):
   idx=stationary_indices(len(x),10000,1/block,np.random.default_rng(21000+100*i+block));intervals.append({'block':block,'paths':10000,'seed':21000+100*i+block,'annual_mean_ci95':np.quantile(x[idx].mean(1)*12,[.025,.975]).tolist()})
  res[name]={'n':len(x),'long_count_min_median':[int(z.Nlong.min()),float(z.Nlong.median())],'short_count_min_median':[int(z.Nshort.min()),float(z.Nshort.median())],'annual_mean':float(x.mean()*12),'SR':float(x.mean()/x.std(ddof=1)*np.sqrt(12)),'bootstrap':intervals,'gate':bool(x.mean()>0 and all(v['annual_mean_ci95'][0]>0 for v in intervals))}
 result={'windows':res,'advance':all(v['gate'] for v in res.values()),'native_replication':False,'strategy_validated':False,'independent_confirmation':False}
 with (O/'results.json').open('x') as f:json.dump(result,f,indent=2)
 print(json.dumps(result,indent=2))
if __name__=='__main__':
 import sys
 register() if '--register' in sys.argv else main()
