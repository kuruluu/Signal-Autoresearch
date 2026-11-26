"""P79 causal adjusted-return allocation screen."""
from pathlib import Path
import json,hashlib
import numpy as np,pandas as pd
from scipy.optimize import minimize
from .reality_check import stationary_indices
R=Path(__file__).resolve().parents[1];B=R/'research/replication_first';O=B/'p79_transfer_001'
def weights(c):
 c=c/np.trace(c)
 f=lambda x:.5*x@c@x-np.log(x).sum()
 g=lambda x:c@x-1/x
 z=minimize(f,np.ones(len(c)),jac=g,bounds=[(1e-9,None)]*len(c),method='L-BFGS-B',options={'ftol':1e-14,'gtol':1e-10,'maxiter':2000});w=z.x/z.x.sum();rc=w*(c@w)/(w@c@w)
 if not np.isfinite(w).all() or (w<=0).any() or np.max(abs(rc-1/len(c)))>1e-5:raise ValueError('ERCfailed')
 v=minimize(lambda x:x@c@x,np.ones(len(c))/len(c),jac=lambda x:2*c@x,bounds=[(0,1)]*len(c),constraints=[{'type':'eq','fun':lambda x:x.sum()-1,'jac':lambda x:np.ones(len(x))}],method='SLSQP',options={'ftol':1e-12,'maxiter':1000})
 if not v.success or abs(v.x.sum()-1)>1e-8:raise ValueError('MVfailed')
 return np.array([w,v.x,np.ones(len(c))/len(c)])
def freeze():
 files=[Path(__file__),R/'researchlab/reality_check.py',O/'registration.json',*[R/'research/data'/f'{s}.csv' for s in ['SPY','IEF','GLD']]]
 with (O/'analysis_freeze.json').open('x') as f:json.dump({'clarification':'Only250returnsby2007end. StartFeb2008afterfirsteligibleJanendestimate. Applyonnextsessionclose,thenearnfollowingreturn;zeroRFSharpe,notnativeFedfundSharpe. Nooutcomesyet.','hashes':{str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}},f,indent=2)
def main():
 s=json.loads((O/'analysis_freeze.json').read_text())
 s['hashes']['researchlab\\p79_allocation.py']=json.loads((O/'registration_addendum.json').read_text())['code_sha256']
 for p,h in s['hashes'].items():assert hashlib.sha256((R/p).read_bytes()).hexdigest()==h
 data=[pd.read_csv(R/'research/data'/f'{s}.csv',index_col='date',parse_dates=True).adj_close for s in ['SPY','IEF','GLD']];p=pd.concat(data,axis=1);assert p.notna().all().all() and p.index.max().year==2023
 ret=p.pct_change(fill_method=None).iloc[1:];held=np.ones((3,3))/3;pending=None;records=[]
 for i in range(len(ret)):
  rr=ret.iloc[i].to_numpy();pr=held@rr;held=held*(1+rr)/(1+pr[:,None])
  if i>=272:records.append((ret.index[i],*pr))
  if pending is not None:held=pending;pending=None
  if i>=251 and (i==len(ret)-1 or ret.index[i+1].month!=ret.index[i].month):pending=weights(ret.iloc[i-251:i+1].cov().to_numpy())
 f=pd.DataFrame([v[1:] for v in records],index=[v[0] for v in records],columns=['ERC','MV','EW']).loc['2008-02':]
 m=(1+f).groupby(f.index.to_period('M')).prod()-1
 assert m.index.equals(pd.period_range('2008-02','2023-12',freq='M'))
 a=m.to_numpy();sr=lambda x:x.mean(-2)/x.std(-2,ddof=1)*np.sqrt(12);point=sr(a);ci=[]
 for b in (3,12,24):
  idx=stationary_indices(len(a),10000,1/b,np.random.default_rng(790000+b));v=sr(a[idx]);ci.append({'block':b,'paths':10000,'seed':790000+b,'ERC_minus_MV_ci95':np.quantile(v[:,0]-v[:,1],[.025,.975]).tolist(),'ERC_minus_EW_ci95':np.quantile(v[:,0]-v[:,2],[.025,.975]).tolist()})
 result={'months':len(a),'sharpe_zero_RF':dict(zip(m.columns,point.tolist())),'bootstrap':ci,'gate':bool(all(v['ERC_minus_MV_ci95'][0]>0 and v['ERC_minus_EW_ci95'][0]>0 for v in ci)),'strategy_validated':False,'native_replication':False}
 with (O/'results.json').open('x') as f:json.dump(result,f,indent=2)
 print(json.dumps(result,indent=2))
if __name__=='__main__':
 import sys
 freeze() if '--freeze' in sys.argv else main()
