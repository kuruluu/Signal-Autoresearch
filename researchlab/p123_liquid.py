"""P123 external sort mechanism, distinct from original cross-sectional regression."""
from pathlib import Path
import json,hashlib,datetime
import pandas as pd,numpy as np
from .reality_check import stationary_indices
R=Path(__file__).resolve().parents[1];B=R/'research/replication_first';O=B/'p123_liquid_001';D=B/'p63_archive/liquid.parquet'
def register():
 O.mkdir(exist_ok=True)
 s={'id':'P123_liquid_001','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Fixed NYSE20percent market capitalization screen, not direct spread or impact measure. External GP high-minus-low VW quintiles, annual June assignment, nextmonth return lag, nonfinancial SIC exclusion. Actual accounting releases/vintage and native breakpoint fidelity not reconstructed. No lagged or quarterly alternatives; no exact replication claim.',
 'windows':{'original':['1963-07','2010-12'],'later':['2013-05','2022-12']},'gate':'Positiveannualarithmeticmean andall95%lowerbounds>0 at3/12/24month10000stationarypaths,seeds1231000+windowindex100+block,bothwindows. Noalpha/CAGR/accountclaim. Percentdivide100,zero-investmentnoRFsubtraction. Noothersignal/endpointsearch. Passonlyexecutionaudit.',
 'hashes':{str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),D,R/'researchlab/reality_check.py']}}
 with (O/'registration.json').open('x') as f:json.dump(s,f,indent=2)
def main():
 s=json.loads((O/'registration.json').read_text())
 for p,h in s['hashes'].items():assert hashlib.sha256((R/p).read_bytes()).hexdigest()==h
 f=pd.read_parquet(D,filters=[('signalname','==','GP'),('port','==','LS')]);assert pd.to_datetime(f.date).max().year==2022;f=f.rename(columns={'ret':'GP'});f.index=pd.to_datetime(f.date).dt.to_period('M');f=f.sort_index();res={}
 for i,(name,(start,end)) in enumerate(s['windows'].items()):
  z=f.loc[start:end];assert z.index.equals(pd.period_range(start,end,freq='M')) and z.GP.notna().all();x=z.GP.to_numpy()/100;intervals=[]
  for block in (3,12,24):
   idx=stationary_indices(len(x),10000,1/block,np.random.default_rng(1231000+100*i+block));intervals.append({'block':block,'paths':10000,'seed':1231000+100*i+block,'annual_mean_ci95':np.quantile(x[idx].mean(1)*12,[.025,.975]).tolist()})
  res[name]={'n':len(x),'long_count_min_median':[int(z.Nlong.min()),float(z.Nlong.median())],'short_count_min_median':[int(z.Nshort.min()),float(z.Nshort.median())],'annual_mean':float(x.mean()*12),'SR':float(x.mean()/x.std(ddof=1)*np.sqrt(12)),'bootstrap':intervals,'gate':bool(x.mean()>0 and all(v['annual_mean_ci95'][0]>0 for v in intervals))}
 result={'windows':res,'advance':all(v['gate'] for v in res.values()),'native_replication':False,'strategy_validated':False,'independent_confirmation':False}
 with (O/'results.json').open('x') as f:json.dump(result,f,indent=2)
 print(json.dumps(result,indent=2))
if __name__=='__main__':
 import sys
 register() if '--register' in sys.argv else main()
