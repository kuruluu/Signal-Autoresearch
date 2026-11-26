"""P63 external reconstruction, not native replication."""
from pathlib import Path
import json,hashlib,datetime
import pandas as pd
import numpy as np
from .reality_check import stationary_indices
ROOT=Path(__file__).resolve().parents[1];B=ROOT/'research/replication_first';O=B/'p63_external_001';D=B/'p63_archive/PredictorLSretWide.parquet'
def measures(a):
 sr=a.mean(-2)/a.std(-2,ddof=1)*np.sqrt(12)
 return a[...,0].mean(-1)*12,sr[...,0]-sr[...,1]
def register():
 O.mkdir(exist_ok=True)
 s={'id':'P63_external_001','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'OSAP2023.08externalreconstruction. Nativeunreproduced: rollingendpointresidualaggregation androwlags differ; do notequate.',
 'windows':{'original_partial':['1930-06','2009-12'],'later':['2012-01','2022-12']},
 'construction':'ResidualMomentum andMom12m samearchive, percentdivide100,pairedcompletecalendar. Zero-investmentnoRFsubtraction. PrimarymeanResidual>0 andSRadvantage>0 inbothwindows. Noalpha numericaltarget claim; noothercolumn/horizon/windowsearch.',
 'inference':'10000pairedstationarypaths3/12/24months seeds630000+100*windowindex+block. Both95%lowerboundspositiveallblocks andwindows. Fixedreturnsnotstockreformation; notindependentconfirmation. NoCAGR/account/costs. Passonlyfeasibilityaudit.',
 'hashes':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),ROOT/'researchlab/reality_check.py',D,B/'p63_archive/ZZ1_ResidualMomentum6m_ResidualMomentum.do',B/'p63_archive/11_ProcessCRSP.R']}}
 with (O/'registration.json').open('x') as f:json.dump(s,f,indent=2)
def main():
 s=json.loads((O/'registration.json').read_text())
 for p,h in s['hashes'].items():
  assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
 f=pd.read_parquet(D,columns=['date','ResidualMomentum','Mom12m']);f.index=pd.to_datetime(f.pop('date')).dt.to_period('M');assert not f.index.duplicated().any();results={}
 for i,(name,(start,end)) in enumerate(s['windows'].items()):
  x=f.loc[start:end]
  assert x.index.equals(pd.period_range(start,end,freq='M')) and x.notna().all().all()
  a=x.to_numpy()/100;m,g=measures(a);intervals=[]
  for block in (3,12,24):
   idx=stationary_indices(len(a),10000,1/block,np.random.default_rng(630000+100*i+block));mm,gg=measures(a[idx]);intervals.append({'block':block,'paths':10000,'seed':630000+100*i+block,'mean_ci95':np.quantile(mm,[.025,.975]).tolist(),'SR_advantage_ci95':np.quantile(gg,[.025,.975]).tolist()})
  results[name]={'n':len(a),'annual_mean':float(m),'SR_advantage':float(g),'bootstrap':intervals,'gate':bool(m>0 and g>0 and all(z['mean_ci95'][0]>0 and z['SR_advantage_ci95'][0]>0 for z in intervals))}
 result={'windows':results,'advance':all(z['gate'] for z in results.values()),'native_replication':False,'strategy_validated':False,'independent_confirmation':False}
 with (O/'results.json').open('x') as f:json.dump(result,f,indent=2)
 print(json.dumps(result,indent=2))
if __name__=='__main__':
 import sys
 register() if '--register' in sys.argv else main()
