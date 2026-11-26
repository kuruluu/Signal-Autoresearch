"""Predeclared monthly ETF bridge; conditional exploratory inference only."""
import json
import time
import numpy as np
import pandas as pd
from .catalog import ROOT,RESEARCH
from .experiment import save
from .integrity import sha
from .p24_reproduction import ols
from .bootstrap import stationary_indices

OUT=RESEARCH/'replication_first/p24_spy_bridge_001'

def rebalance(equity,old_risky,weight,cost):
    sign=np.sign(weight*equity-old_risky)
    after=(equity+cost*sign*old_risky)/(1+cost*sign*weight)
    risky=weight*after
    fee=cost*abs(risky-old_risky)
    return after,risky,after-risky,fee

def simulate(weights,risky_returns,cash_returns,cost):
    equity=1.;risky=0.;rows=[]
    for i,date in enumerate(weights.index):
        before=equity
        after,risky,cash,fee=rebalance(equity,risky,float(weights.loc[date]),cost)
        risky*=1+float(risky_returns.loc[date]);cash*=1+float(cash_returns.loc[date])
        equity=risky+cash
        if i==len(weights)-1:
            fee+=cost*risky;equity-=cost*risky;risky=0
        rows.append({'month':str(date),'net_return':equity/before-1,'equity':equity,'weight':weights.loc[date],
                     'cost_fraction':fee/before,'cash_return':cash_returns.loc[date]})
    return pd.DataFrame(rows).set_index('month')

def holm(p):
    p=np.asarray(p);order=np.argsort(p);out=np.empty(len(p))
    out[order]=np.minimum(1,np.maximum.accumulate(p[order]*(len(p)-np.arange(len(p)))))
    return out

def bootstrap_alphas(y,x,block,count=5000):
    idx=stationary_indices(len(y),count,block,24001)
    y=np.asarray(y);x=np.asarray(x)
    def intercept(y,x,axis):
        ym=y.mean(axis=axis);xm=x.mean(axis=axis)
        cov=(y*x).mean(axis=axis)-ym*xm;var=(x*x).mean(axis=axis)-xm*xm
        return ym-cov/var*xm
    observed=intercept(y,x,0)
    sims=intercept(y[idx],x[idx],1)
    p=(1+((sims-observed)>=observed).sum(axis=0))/(count+1)
    return {'alpha_annual_pct':observed*1200,'low_annual_pct':np.quantile(sims,.025,axis=0)*1200,
            'high_annual_pct':np.quantile(sims,.975,axis=0)*1200,'p_raw':p,'p_holm':holm(p),
            'p_monte_carlo_se':np.sqrt(p*(1-p)/count),'paths':count}

def register():
    OUT.mkdir(parents=True,exist_ok=True)
    inputs=[RESEARCH/'data/SPY.csv',RESEARCH/'replication_first/p24_inputs/author_daily_2021.csv']
    spec={'id':'p24_spy_bridge_001','parent':'p24_partial_001','classification':'ETF transfer and signal feasibility; not faithful replication or independent confirmation',
      'stages':['matched 2012-2020 CRSP daily-compounded market/full-sample scaling','SPY instrument change/full-sample scaling',
                'SPY calibration-only scaling','SPY calibration-only scaling capped at 1','SPY next-open execution with net-order costs'],
      'calibration':['2008-01','2011-12'],'evaluation':['2012-01','2020-12'],
      'variance':'prior full calendar-month daily excess-return variance, ddof0; RF from author archived daily data; exact date alignment required',
      'normalization':'c = sd(monthly SPY excess)/sd(monthly SPY excess/lagged variance) on calibration only, frozen thereafter',
      'signal':'monthly SPY weight min(1,c/prior-month variance), no shorting or leverage; no parameter sweep',
      'execution':'previous month close signal, first exchange session open to next month first open; synthetic adjusted units; net-order fees self financed; final liquidation',
      'cash':'compound archived daily RF from entry-session date through session preceding exit; realized cash accrual approximation, not a decision feature; monthly-close diagnostic uses matching monthly compounded RF',
      'controls':'same-execution full SPY and fixed calibration-volatility-matched SPY allocation (ratio of capped-strategy/calibration-market standard deviations, capped at 1). No realized test-period risk matching.',
      'cost_bps_per_side':[5,10,20],
      'primary':'net monthly alpha on same-execution market excess return; positive risk-adjusted usefulness requires base alpha>=1 pp/year, positive lower95 bound and Holm p<=.05 at all predeclared block lengths; positive alpha at 2x/4x costs',
      'secondary':'return, drawdown, turnover/cost, exposure and return versus calibration risk control; not alternative success gates',
      'inference':'5000 synchronized stationary bootstrap paths, block lengths 6/12/24 months, seed24001, refit alpha each path; Holm across 3 cost scenarios. Conditional on frozen calibration c. Diagnostic bridge alphas not additional discovery claims.',
      'precision_rule':'If any base adjusted p in [.04,.06], increase all block runs to 20000; decision still requires all blocks. Report Monte Carlo SE.',
      'limitations':['All periods previously examined','108 evaluation months limits power','Revised surviving SPY data','Daily RF and adjusted units approximate actual cash/dividend accounting','Academic full-sample stages explicitly noncausal','Opening prices not guaranteed fills','This is a monthly signal, not a demonstrated several-day effect'],
      'input_hashes':{str(p.relative_to(ROOT)):sha(p) for p in inputs},
      'code_hashes':{name:sha(ROOT/'researchlab'/name) for name in ['p24_bridge.py','p24_reproduction.py','bootstrap.py']},
      'sealed_final_access':False}
    file=OUT/'registration.json'
    if file.exists():
        if json.loads(file.read_text())['spec']!=spec:raise ValueError('Bridge definition changed; new version required')
    else:save(file,{'registered_at_unix':time.time(),'spec':spec})
    return spec

def run():
    spec=register()
    spy=pd.read_csv(RESEARCH/'data/SPY.csv',index_col='date',parse_dates=True)
    author=pd.read_csv(RESEARCH/'replication_first/p24_inputs/author_daily_2021.csv',index_col='date',parse_dates=True)
    daily=pd.DataFrame({'SPY':spy.adj_close.pct_change(fill_method=None),'CRSP':author.vwretd,'rf':author.rf}).loc['2007-02-01':'2020-12-31']
    if daily.isna().any().any():raise ValueError('Unmatched daily returns or RF')
    months=daily.index.to_period('M')
    total=(1+daily).groupby(months).prod()-1
    excess=total[['SPY','CRSP']].sub(total.rf,axis=0)
    rv=daily[['SPY','CRSP']].sub(daily.rf,axis=0).groupby(months).var(ddof=0).shift(1)
    train=excess.loc['2008-01':'2011-12'].index;test=excess.loc['2012-01':'2020-12'].index
    assert len(train)==48 and len(test)==108
    c=excess.SPY.loc[train].std()/(excess.SPY/rv.SPY).loc[train].std()
    causal=(c/rv.SPY);capped=causal.clip(upper=1)
    control=min(1,(capped.loc[train]*excess.SPY.loc[train]).std()/excess.SPY.loc[train].std())
    stages={}
    for asset in ['CRSP','SPY']:
        f=excess[asset].loc[test];u=(excess[asset]/rv[asset]).loc[test]
        norm=f.std()/u.std();stages[asset+'_full_sample']=ols(u*norm,f,hac_lags=6)
    stages['SPY_causal']=ols((causal*excess.SPY).loc[test],excess.SPY.loc[test],hac_lags=6)
    stages['SPY_causal_capped']=ols((capped*excess.SPY).loc[test],excess.SPY.loc[test],hac_lags=6)
    save(OUT/'diagnostic_stages.json',stages)
    open_dates=spy.groupby(spy.index.to_period('M')).apply(lambda f:f.index[0]).to_dict()
    risky={};cash={};entries=[]
    for month in test:
        entry=open_dates[month];exit=open_dates[month+1]
        risky[month]=spy.adj_open.loc[exit]/spy.adj_open.loc[entry]-1
        rf=author.rf.loc[(author.index>=entry)&(author.index<exit)]
        expected=spy.loc[(spy.index>=entry)&(spy.index<exit)].index
        if not rf.index.equals(expected) or rf.isna().any():raise ValueError('Cash interval incomplete')
        cash[month]=(1+rf).prod()-1
        entries.append({'month':str(month),'signal_close':str(spy.loc[spy.index<entry].index[-1].date()),'entry':str(entry.date()),'exit':str(exit.date())})
    r=pd.Series(risky);rf=pd.Series(cash);w=capped.loc[test]
    data=[];ys=[];xs=[];frames=[]
    for bps in spec['cost_bps_per_side']:
        strategies={'signal':w,'market':w*0+1,'calibration_risk_control':w*0+control}
        output={key:simulate(weights,r,rf,bps/10000) for key,weights in strategies.items()}
        for name,frame in output.items():frame.to_csv(OUT/f'{name}_{bps}bps_monthly.csv')
        y=output['signal'].net_return-output['signal'].cash_return
        x=output['market'].net_return-output['market'].cash_return
        ys.append(y.to_numpy());xs.append(x.to_numpy())
        result=ols(y,x,hac_lags=6);f=output['signal'];bm=output['market'];ctrl=output['calibration_risk_control']
        result.update(cost_bps=bps,net_cagr=f.equity.iloc[-1]**(12/len(f))-1,
          market_cagr=bm.equity.iloc[-1]**(12/len(f))-1,control_cagr=ctrl.equity.iloc[-1]**(12/len(f))-1,
          mean_entry_weight=w.mean(),max_entry_weight=w.max(),max_drawdown=(f.equity/f.equity.cummax().clip(lower=1)-1).min(),
          mean_net_minus_control_annual=(f.net_return-ctrl.net_return).mean()*12,
          mean_cost_fraction=f.cost_fraction.mean()*12)
        data.append(result)
    Y=np.column_stack(ys);X=np.column_stack(xs)
    stats={b:bootstrap_alphas(Y,X,b) for b in (6,12,24)}
    if any(.04<=s['p_holm'][0]<=.06 for s in stats.values()):
        stats={b:bootstrap_alphas(Y,X,b,20000) for b in stats}
    eligible=(data[0]['alpha_annual_pct']>=1 and all(s['low_annual_pct'][0]>0 and s['p_holm'][0]<=.05 for s in stats.values()) and all(v['alpha_annual_pct']>0 for v in data[1:]))
    save(OUT/'results.json',{'calibration_c':c,'calibration_volatility_matched_control_weight':control,'metrics':data,
           'bootstrap':stats,'eligible_for_further_research':eligible,'confirmed_signal':False})
    save(OUT/'execution_dates.json',entries)
    save(OUT/'completion.json',{'completed':True,'stages':5,'cost_scenarios':3,'evaluation_months':108,'holdout_used':False})
    print((OUT/'results.json').read_text())

if __name__=='__main__':run()
