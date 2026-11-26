"""One preselected author commodity-carry series, no cross-asset search."""
from pathlib import Path
import datetime,hashlib,json
import openpyxl
import numpy as np
import pandas as pd
from .reality_check import stationary_indices
R=Path(__file__).resolve().parents[1];B=R/'research/replication_first'
D=B/'p127_audit';O=B/'p127_external_001'

def register():
    O.mkdir(exist_ok=True)
    s={'id':'P127_external_001','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
       'series':'COM column, XSEC - Carry1m sheet, author original and global update. Month-end rank weighting, long1/short1. One-month current curve carry, not average1-12 or timing sheets.',
       'windows':{'original':['1980-02','2012-09'],'later':['2018-03','2021-07']},
       'gate':'Original SR within0.03 of NBER2013TableII0.60; original and later mean positive with all95percent stationary bootstrap3/12/24month10000path lower bounds positive. Seeds127000+100*windowindex+block. Later only41months, uncertainty/power limited; failure is not proof of no effect. No alternative class/window/carry variant.',
       'units':'Raw workbook units initially unresolved. SR and sign/bootstrap-positive decision invariant to positive unit scaling. Report raw mean explicitly; no percent/account/CAGR claim until unit provenance resolved. No RF subtraction on zero-investment excess series.',
       'vintage':'Original NBER2013 method/version, final JFE2018 identity. Update methodological equivalence not independently rebuilt. Original/update overlap maxdifference reported diagnostically, never used to select a variant. Gap2012Oct-2018Feb excluded from persistence gate; working draft2013, final issue2018Feb.',
       'limits':'Historical author series, not independent confirmation, executable futures/account strategy, or full published replication. Sealed2024-2025 untouched.',
       'hashes':{str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),D/'strategy_returns.xlsx',D/'strategy_returns_-_global.xlsx',D/'working.pdf',R/'researchlab/reality_check.py']}}
    with (O/'registration.json').open('x') as f:json.dump(s,f,indent=2)

def read(path):
    w=openpyxl.load_workbook(path,read_only=True,data_only=True)
    rows=iter(w['XSEC - Carry1m'].values);headers=next(rows);col=headers.index('COM');out=[]
    for row in rows:
        if hasattr(row[0],'year') and isinstance(row[col],(int,float)):
            out.append((pd.Period(row[0],freq='M'),float(row[col])))
    return pd.Series(dict(out)).sort_index()

def main():
    s=json.loads((O/'registration.json').read_text())
    for p,h in s['hashes'].items():
        if hashlib.sha256((R/p).read_bytes()).hexdigest()!=h:raise ValueError('Changed frozen input')
    original=read(D/'strategy_returns.xlsx');update=read(D/'strategy_returns_-_global.xlsx')
    assert original.index.max()==pd.Period('2012-09') and update.index.max()==pd.Period('2021-07')
    common=original.index.intersection(update.index);delta=float(abs(original[common]-update[common]).max());results={}
    for wi,(name,(start,end)) in enumerate(s['windows'].items()):
        z=(original if name=='original' else update).loc[start:end]
        assert z.index.equals(pd.period_range(start,end,freq='M')) and np.isfinite(z).all()
        x=z.to_numpy();ci=[]
        for block in (3,12,24):
            seed=127000+100*wi+block;idx=stationary_indices(len(x),10000,1/block,np.random.default_rng(seed))
            ci.append({'block':block,'paths':10000,'seed':seed,'mean_monthly_raw_ci95':np.quantile(x[idx].mean(1),[.025,.975]).tolist()})
        results[name]={'n':len(x),'mean_monthly_raw':float(x.mean()),'annualized_SR':float(x.mean()/x.std(ddof=1)*np.sqrt(12)),'bootstrap':ci,'gate':bool(x.mean()>0 and all(y['mean_monthly_raw_ci95'][0]>0 for y in ci))}
    match=abs(results['original']['annualized_SR']-.60)<=.03
    r={'windows':results,'numerical_SR_match':match,'overlap_months':len(common),'overlap_max_abs_raw_difference':delta,'advance':bool(match and all(x['gate'] for x in results.values())),'strategy_validated':False,'independent_confirmation':False}
    with (O/'results.json').open('x') as f:json.dump(r,f,indent=2)
    print(json.dumps(r,indent=2))

if __name__=='__main__':
    import sys
    register() if '--register' in sys.argv else main()
