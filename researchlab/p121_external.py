"""P121 external sort mechanism, distinct from original cross-sectional regression."""
from pathlib import Path
import json,hashlib,datetime
import pandas as pd,numpy as np
from .reality_check import stationary_indices
R=Path(__file__).resolve().parents[1];B=R/'research/replication_first';O=B/'p121_external_001';D=B/'p63_archive/PredictorLSretWide.parquet'
def register():
 O.mkdir(exist_ok=True)
 s={'id':'P121_external_001','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'External annual AssetGrowth low-minus-high EW deciles. Annual June assignment and nextmonth return lag. Accounting table availability/vintage not reconstructed; not exact native replication. Annual signal selected before outcomes, no quarterly alternative.',
 'windows':{'original':['1968-07','2003-06'],'later':['2008-09','2022-12']},'gate':'Positiveannualarithmeticmean andall95%lowerbounds>0 at3/12/24month10000stationarypaths,seeds1210000+windowindex100+block,bothwindows. Noalpha/CAGR/accountclaim. Percentdivide100,zero-investmentnoRFsubtraction. Noothersignal/endpointsearch. Passonlyexecutionaudit.',
 'hashes':{str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),D,R/'researchlab/reality_check.py']}}
 with (O/'registration.json').open('x') as f:json.dump(s,f,indent=2)
def main():
 s=json.loads((O/'registration.json').read_text())
 for p,h in s['hashes'].items():assert hashlib.sha256((R/p).read_bytes()).hexdigest()==h
 f=pd.read_parquet(D,columns=['date','AssetGrowth']);f.index=pd.to_datetime(f.date).dt.to_period('M');res={}
 for i,(name,(start,end)) in enumerate(s['windows'].items()):
  z=f.loc[start:end];assert z.index.equals(pd.period_range(start,end,freq='M')) and z.AssetGrowth.notna().all();x=z.AssetGrowth.to_numpy()/100;intervals=[]
  for block in (3,12,24):
   idx=stationary_indices(len(x),10000,1/block,np.random.default_rng(1210000+100*i+block));intervals.append({'block':block,'paths':10000,'seed':1210000+100*i+block,'annual_mean_ci95':np.quantile(x[idx].mean(1)*12,[.025,.975]).tolist()})
  res[name]={'n':len(x),'annual_mean':float(x.mean()*12),'SR':float(x.mean()/x.std(ddof=1)*np.sqrt(12)),'bootstrap':intervals,'gate':bool(x.mean()>0 and all(v['annual_mean_ci95'][0]>0 for v in intervals))}
 result={'windows':res,'advance':all(v['gate'] for v in res.values()),'native_replication':False,'strategy_validated':False,'independent_confirmation':False}
 with (O/'results.json').open('x') as f:json.dump(result,f,indent=2)
 print(json.dumps(result,indent=2))
if __name__=='__main__':
 import sys
 register() if '--register' in sys.argv else main()
