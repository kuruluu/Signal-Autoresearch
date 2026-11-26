"""Frozen nominal-calendar SPY effect and idealized payoff hurdle."""
from pathlib import Path
import datetime,hashlib,json
import numpy as np
import pandas as pd
from .p126_calendar import classify
from .reality_check import stationary_indices
R=Path(__file__).resolve().parents[1];B=R/'research/replication_first'
O=B/'p126_transfer_001';D=R/'research/data/SPY.csv';C=B/'p126_later_audit/completion.json'

def register():
    O.mkdir(exist_ok=True)
    s={'id':'P126_transfer_001','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
       'windows':{'pre_issue_diagnostic':['2017-01','2019-10'],'post_issue':['2019-11','2023-12']},
       'clock':'Nominal scheduled dates; retain cancelled March18,2020 mechanically. This is a prospective adaptation, not actual-meeting causal replication. Reset minus6 weekdays; even weeks0/2/4/6. No holiday/COVID removal or alternate clock.',
       'effect':'SPY adjusted-close total daily returns, zero on weekdays without sessions. Even-minus-odd mean daily return, exclude beyond33 only for this descriptive comparison. Cash benchmark0, no RF-subtracted native claim.',
       'payoff':'At each prior exchange-session close target full SPY for next session return if that date is even week, else cash with zero interest; beyond33 cash. Perfect fractional sizing, no fees/spread/slippage, idealized rejection hurdle only. Benchmark always SPY. Include all actual sessions and beyond33. Return-series division yields exact log growth difference. No10k accounting or strategy-validation claim.',
       'gate':'Post_issue effect contrast and annual log-growth advantage must have all95percent lower bounds>0 for3/12/24month stationary paired bootstrap10000paths seeds126300+100*windowindex+block. Diagnostic not admission gate. No parameter/window search after failure. If pass, separate observed-cost account test and project-wide confirmation required.',
       'hashes':{str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),D,C,R/'researchlab/p126_calendar.py',R/'researchlab/reality_check.py']},
       'limits':'Already viewed development years. Not independent confirmation or final2019paper replication. Sealed financial observations2024-2025 untouched;2024boundary schedule metadata only.'}
    with (O/'registration.json').open('x') as f:json.dump(s,f,indent=2)

def contrast(a):
    return a[...,0].sum(-1)/a[...,1].sum(-1)-a[...,2].sum(-1)/a[...,3].sum(-1)

def main():
    s=json.loads((O/'registration.json').read_text())
    for p,h in s['hashes'].items():
        if hashlib.sha256((R/p).read_bytes()).hexdigest()!=h:raise ValueError('Frozen input changed')
    f=pd.read_csv(D,parse_dates=['date']).set_index('date').sort_index()
    if f.index.max().year!=2023 or not f.index.is_unique:raise ValueError('Unexpected source bounds')
    ret=f.adj_close.pct_change(); schedule=json.loads(C.read_text())
    meetings=pd.to_datetime(['2016-12-14']+[x['date'] for x in schedule['rows']]+[schedule['boundary']['date']])
    cal=classify(pd.bdate_range('2017-01-01','2023-12-31'),meetings).set_index('date')
    # Missing weekday rows are closed-market sessions, under the audited source.
    cal['ret']=ret.reindex(cal.index).fillna(0)
    cal['session']=cal.index.isin(f.index)
    even=cal.week.isin([0,2,4,6])&cal.included
    odd=cal.week.isin([-1,1,3,5])&cal.included
    cal['position']=even.astype(int)
    cal['log_advantage']=np.where(even,0,-np.log1p(cal.ret))
    v=pd.DataFrame({'es':cal.ret*even,'en':even.astype(int),'os':cal.ret*odd,'on':odd.astype(int),'lg':cal.log_advantage},index=cal.index).groupby(cal.index.to_period('M')).sum()
    results={}
    for wi,(name,(start,end)) in enumerate(s['windows'].items()):
        z=v.loc[start:end];assert z.index.equals(pd.period_range(start,end,freq='M'))
        a=z.to_numpy();cis=[]
        for block in (3,12,24):
            seed=126300+100*wi+block;idx=stationary_indices(len(a),10000,1/block,np.random.default_rng(seed));draw=a[idx]
            cis.append({'block':block,'paths':10000,'seed':seed,'daily_contrast_ci95':np.quantile(contrast(draw),[.025,.975]).tolist(),'annual_log_advantage_ci95':np.quantile(draw[...,4].mean(1)*12,[.025,.975]).tolist()})
        ss=cal.loc[start:end];session=ss[ss.session];changes=int(session.position.diff().abs().fillna(abs(session.position.iloc[0])).sum())
        results[name]={'months':len(a),'daily_contrast':float(contrast(a)),'annual_log_advantage':float(a[:,4].mean()*12),'position_changes_including_entry':changes,'fractional_zero_cost_only':True,'bootstrap':cis,'gate':bool(all(x['daily_contrast_ci95'][0]>0 and x['annual_log_advantage_ci95'][0]>0 for x in cis))}
    r={'windows':results,'advance':results['post_issue']['gate'],'strategy_validated':False,'independent_confirmation':False,'capital_account_simulated':False}
    with (O/'results.json').open('x') as f:json.dump(r,f,indent=2)
    print(json.dumps(r,indent=2))

if __name__=='__main__':
    import sys
    register() if '--register' in sys.argv else main()
