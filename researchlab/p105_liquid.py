"""One fixed liquidity-screen persistence test."""
from pathlib import Path
import json,hashlib
import numpy as np,pandas as pd
from .reality_check import stationary_indices
R=Path(__file__).resolve().parents[1];B=R/'research/replication_first';O=B/'p105_liquid_001';D=B/'p63_archive/liquid.parquet'
def freeze():
 with (O/'analysis_freeze.json').open('x') as f:json.dump({'clarification':'2011archive typo means2023.08 perexactrevision','hashes':{str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),R/'researchlab/reality_check.py',O/'registration.json',D]}},f,indent=2)
def main():
 s=json.loads((O/'analysis_freeze.json').read_text())
 for p,h in s['hashes'].items():assert hashlib.sha256((R/p).read_bytes()).hexdigest()==h
 f=pd.read_parquet(D);assert pd.to_datetime(f.date).max().year==2022;f=f[(f.signalname=='CustomerMomentum')&(f.port=='LS')].copy();f.index=pd.to_datetime(f.date).dt.to_period('M');f=f.loc['2009-01':'2022-12'];assert f.index.equals(pd.period_range('2009-01','2022-12',freq='M'));x=f.ret.to_numpy()/100;assert np.isfinite(x).all();ci=[]
 for b in (3,12,24):
  idx=stationary_indices(len(x),10000,1/b,np.random.default_rng(1051000+b));ci.append({'block':b,'paths':10000,'seed':1051000+b,'annual_mean_ci95':np.quantile(x[idx].mean(1)*12,[.025,.975]).tolist()})
 r={'n':len(x),'annual_mean':float(x.mean()*12),'SR':float(x.mean()/x.std(ddof=1)*np.sqrt(12)),'long_count_min_median':[int(f.Nlong.min()),float(f.Nlong.median())],'short_count_min_median':[int(f.Nshort.min()),float(f.Nshort.median())],'bootstrap':ci,'gate':bool(x.mean()>0 and all(z['annual_mean_ci95'][0]>0 for z in ci)),'strategy_validated':False}
 with (O/'results.json').open('x') as f:json.dump(r,f,indent=2)
 print(json.dumps(r,indent=2))
if __name__=='__main__':
 import sys
 freeze() if '--freeze' in sys.argv else main()
