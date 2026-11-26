"""Fixed native aggregate 50/50 diversification reconstruction."""
import json,hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from openpyxl import load_workbook
from .reality_check import stationary_indices

ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'research/replication_first';OUT=BASE/'p09_partial_001'


def paired(rows,start='1972-01',end='2011-07'):
    header=None;selected=[];seen=set()
    for row in rows:
        if row and str(row[0]).strip()=='DATE':
            header=list(row);continue
        if header is None or not row:continue
        token=str(row[0]).strip()
        if len(token)!=8 or not token.isdigit():continue
        # Two invalid month-end labels in the pinned source; no return edits.
        token={'20100931':'20100930','20101131':'20101130'}.get(token,token)
        date=pd.to_datetime(token,format='%Y%m%d').to_period('M')
        if not pd.Period(start,'M')<=date<=pd.Period(end,'M'):continue
        if date in seen:raise ValueError('Duplicate month')
        seen.add(date)
        selected.append([date,row[header.index('VAL')],row[header.index('MOM')]])
    if header is None:raise ValueError('Missing DATE header')
    frame=pd.DataFrame(selected,columns=['month','value','momentum']).set_index('month').sort_index()
    expected=pd.period_range(start,end,freq='M')
    frame=frame.reindex(expected).apply(pd.to_numeric,errors='raise')
    finite=np.isfinite(frame.to_numpy()).all(axis=1)
    missing=[str(d) for d in frame.index[~finite]]
    return frame.loc[finite],missing


def measures(a):
    # Final axes: observation, two factors; arbitrary preceding bootstrap axes.
    mean=a.mean(axis=-2);sd=a.std(axis=-2,ddof=1)
    sr=np.sqrt(12)*mean/sd
    combo=a.mean(axis=-1);cs=np.sqrt(12)*combo.mean(axis=-1)/combo.std(axis=-1,ddof=1)
    centered=a-mean[...,None,:]
    corr=(centered[...,0]*centered[...,1]).sum(axis=-1)/np.sqrt((centered[...,0]**2).sum(axis=-1)*(centered[...,1]**2).sum(axis=-1))
    return sr,cs,corr


def main():
    spec=json.loads((OUT/'registration.json').read_text())
    for name,digest in spec['hashes'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest
    freeze=json.loads((OUT/'registration_addendum.json').read_text());assert freeze['code_sha256']==hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    assert not (OUT/'results.json').exists()
    book=load_workbook(BASE/'p09_audit/VME_Factors.xlsx',read_only=True,data_only=True)
    frame,missing=paired(book['AMP VME Factors'].values);book.close()
    if len(frame)<450:raise ValueError('Registered minimum paired sample not met')
    a=frame.to_numpy();sr,combo,corr=measures(a);intervals=[]
    for block in (3,12,24):
        rng=np.random.default_rng(90300+block);correlations=[];gains=[]
        for offset in range(0,10000,100):
            idx=stationary_indices(len(a),100,1/block,rng);s,c,r=measures(a[idx])
            correlations.extend(r);gains.extend(c-s.max(axis=-1))
        intervals.append({'block_months':block,'paths':10000,'seed':90300+block,
                          'correlation_ci95':np.quantile(correlations,[.025,.975]).tolist(),
                          'combo_sharpe_advantage_ci95':np.quantile(gains,[.025,.975]).tolist()})
    numerical=bool((np.abs(np.r_[sr,combo]-[.72,.74,1.59])<=.1).all() and abs(corr+.6)<=.05)
    result={'type':'Partial native aggregate diversification reconstruction; ex-post global weights',
            'n_months':len(frame),'missing_months':missing,'sharpe_value_momentum':sr.tolist(),'sharpe_combo':float(combo),
            'correlation':float(corr),'combo_sharpe_advantage':float(combo-sr.max()),
            'numerical_gate_pass':numerical,'bootstrap':intervals,
            'advance_to_causal_execution_audit':bool(numerical and all(r['correlation_ci95'][1]<0 and r['combo_sharpe_advantage_ci95'][0]>0 for r in intervals)),
            'independent_confirmation':False,'trading_strategy_validated':False}
    (OUT/'results.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))


if __name__=='__main__':main()
