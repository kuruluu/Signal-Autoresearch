"""Native-window FOMC-cycle contrasts using a dated French factor release."""
from pathlib import Path
import json,hashlib,datetime,re
import numpy as np
import pandas as pd
from .p126_calendar import classify
from .reality_check import stationary_indices
R=Path(__file__).resolve().parents[1];B=R/'research/replication_first';O=B/'p126_native_001'
D=B/'p52_audit/F-F_Research_Data_Factors_daily.CSV';C=B/'p126_audit/completion.json'

def register():
    O.mkdir(exist_ok=True)
    s={'id':'P126_native_001','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
       'target':'February12,2018 working draft Table1A, not certified final2019 replication.1994-2016 weekdays;184 meetings plus boundaries; holidays/closures zero; beyond33 excluded.',
       'construction':'French202008 Mkt-RF percent divided100. Even weeks0,2,4,6 versus odd-1,1,3,5; second contrast2,4,6 versus same odd baseline, omitting week0. Calendar reset nextmeeting-minus6 weekdays. Month paired return sums and day counts preserve weighted daily means.',
       'numerical':'Overall contrast within.0002 of.00120 and246contrast within.0002 of.00109 (2bps/day tolerances for dated vintage).',
       'gate':'Both numerical matches and all95percent lower bounds positive for both contrasts,3/12/24month stationary bootstrap10000paths seeds126000+block. Preliminary per-paper inference, not independent or project-wide confirmation. No alternate days, tolerance or sample search.',
       'limits':'Native-window market contrast, not causal monetary policy identification, contemporary persistence, payoff or account strategy. Already viewed development history; sealed2024-2025 untouched.',
       'hashes':{str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),R/'researchlab/p126_calendar.py',R/'researchlab/reality_check.py',D,C]}}
    with (O/'registration.json').open('x') as f:json.dump(s,f,indent=2)

def contrasts(a):
    odd=a[...,2].sum(-1)/a[...,3].sum(-1)
    return np.stack([a[...,0].sum(-1)/a[...,1].sum(-1)-odd,a[...,4].sum(-1)/a[...,5].sum(-1)-odd],axis=-1)

def main():
    s=json.loads((O/'registration.json').read_text())
    for p,h in s['hashes'].items():
        if hashlib.sha256((R/p).read_bytes()).hexdigest()!=h:raise ValueError('Frozen input changed')
    rows=[]
    for line in D.read_text().splitlines():
        if re.match(r'^\d{8},',line):
            x=line.split(',');rows.append((pd.to_datetime(x[0]),float(x[1])/100))
    f=pd.Series(dict(rows)).sort_index()
    if f.index.max().year!=2020:raise ValueError('Unexpected vintage dates')
    m=pd.to_datetime(['1993-12-21']+[x['date'] for x in json.loads(C.read_text())['rows']]+['2017-02-01'])
    cal=classify(pd.bdate_range('1994-01-01','2016-12-31'),m).set_index('date')
    ret=f.reindex(cal.index);missing=ret.index[ret.isna()].strftime('%Y-%m-%d').tolist();cal['ret']=ret.fillna(0)
    cal=cal[cal.included];assert len(cal)==5997
    even=cal.week.isin([0,2,4,6]);odd=cal.week.isin([-1,1,3,5]);other=cal.week.isin([2,4,6]);x=cal.ret.to_numpy()
    a=pd.DataFrame(np.column_stack([x*even,even.astype(int),x*odd,odd.astype(int),x*other,other.astype(int)]),index=cal.index).groupby(cal.index.to_period('M')).sum().to_numpy()
    assert len(a)==276 and np.isfinite(a).all()
    point=contrasts(a);ci=[]
    for block in (3,12,24):
        idx=stationary_indices(len(a),10000,1/block,np.random.default_rng(126000+block))
        ci.append({'block':block,'paths':10000,'seed':126000+block,'daily_contrast_ci95':np.quantile(contrasts(a[idx]),[.025,.975],axis=0).tolist()})
    numerical=bool(np.all(abs(point-np.array([.00120,.00109]))<=.0002))
    r={'rows':len(cal),'months':len(a),'contrast_order':['all_even_minus_odd','weeks246_minus_odd'],'daily_contrasts':point.tolist(),'numerical_match':numerical,'bootstrap':ci,'advance':bool(numerical and all(np.array(c['daily_contrast_ci95'])[0].min()>0 for c in ci)),'missing_weekdays_zero_filled':missing,'native_version':'2018draft,202008data vintage','strategy_validated':False,'independent_confirmation':False}
    with (O/'results.json').open('x') as f:json.dump(r,f,indent=2)
    print(json.dumps({k:v for k,v in r.items() if k!='missing_weekdays_zero_filled'},indent=2))

if __name__=='__main__':
    import sys
    register() if '--register' in sys.argv else main()
