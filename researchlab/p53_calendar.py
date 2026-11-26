"""Calendar-aware P53 continuation, preserving original abort."""
import json,hashlib,datetime
from pathlib import Path
import numpy as np
import pandas as pd
from .p53_trend import ROOT,BASE,DATA,panel,alpha
from .reality_check import stationary_indices
OUT=BASE/'p53_calendar_001'
def register():
 OUT.mkdir(exist_ok=True)
 s=json.loads((BASE/'p53_partial_001/registration.json').read_text());s.pop('hashes');s.update(id='P53_calendar_001',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),gap_rule='Exactfourmissing1914Aug-Novonly. Splitatgap, resetallstates,applysame61indexwarmuppersegment. Nozero/fill, noPnLacrossclosure. Historicalwindowunchangedbutmissingandpostrestartwarmupexcluded; partialsampleexplicit. Bootstrapseparatelywithineachcontiguousscoresegment, thencombine, avoidingartificialadjacency. Nooutcomesyet.',source='FRBNY1915firstannualreport:NYSEclosedJuly31,1914;restrictedstocktradingDecember12. https://fraser.stlouisfed.org/files/docs/historical/frbny/1915_frb_newyork.pdf')
 s['hashes']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),ROOT/'researchlab/p53_trend.py',ROOT/'researchlab/reality_check.py',DATA]}
 with (OUT/'registration.json').open('x') as f:json.dump(s,f,indent=2)
def main():
 s=json.loads((OUT/'registration.json').read_text())
 for p,h in s['hashes'].items():
  if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise ValueError('Frozenchanged')
 f=pd.read_csv(DATA,parse_dates=['date']).set_index('date').loc['1896-05':'2023-10'];p=f.value.groupby(f.index.to_period('M')).last();missing=pd.period_range('1896-05','2023-10',freq='M').difference(p.index)
 assert list(map(str,missing))==['1914-08','1914-09','1914-10','1914-11']
 segments=[panel(p.loc[:'1914-07']),panel(p.loc['1914-12':])];results={}
 for i,(name,(start,end)) in enumerate(s['windows'].items()):
  parts=[];coverage=[]
  for a in segments:
   labels=a.index.year*100+a.index.month;a=a.loc[(labels>=start)&(labels<=end)]
   if len(a):parts.append(a.to_numpy());coverage.append([str(a.index[0]),str(a.index[-1]),len(a)])
  x=np.concatenate(parts);intervals=[]
  for block in (3,12,24):
   rng=np.random.default_rng(530000+i*100+block);samples=[z[stationary_indices(len(z),10000,1/block,rng)] for z in parts];ci=np.quantile(alpha(np.concatenate(samples,axis=1)),[.025,.975]).tolist();intervals.append({'block':block,'paths':10000,'seed':530000+i*100+block,'alpha_ci95':ci})
  results[name]={'coverage':coverage,'n':len(x),'mean_trend':float(x[:,0].mean()),'monthly_alpha':float(alpha(x)),'bootstrap':intervals,'gate':bool(x[:,0].mean()>0 and alpha(x)>0 and all(z['alpha_ci95'][0]>0 for z in intervals))}
 result={'windows':results,'advance':all(z['gate'] for z in results.values()),'exact_replication':False,'strategy_validated':False,'independent_confirmation':False}
 with (OUT/'results.json').open('x') as f:json.dump(result,f,indent=2)
 print(json.dumps(result,indent=2))
if __name__=='__main__':
 import sys
 register() if '--register' in sys.argv else main()
