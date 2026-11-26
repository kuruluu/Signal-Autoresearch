"""Registered whole-share P118 execution screen; no broker order calls."""
import json,hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from .p118_forecast import ROOT,BASE,panel,riskfree,slope
from .reality_check import stationary_indices

OUT=BASE/'p118_strategy_001';INPUT=BASE/'p118_execution_inputs'


def signals(prices):
    total=prices.adj_close.pct_change(fill_method=None);intra=prices.close/prices.open-1
    night=(1+total)/(1+intra)-1
    monthly=(1+night).groupby(prices.index.to_period('M')).prod().loc['1993-02':]-1
    value=0.;values=[]
    for r in monthly:value=(r+120*value)/121;values.append(value)
    f=pd.Series(values,index=monthly.index);f=f.groupby(f.index.asfreq('Q')).last();f.index+=1
    return f


def allocations(training,future):
    targets={};control={}
    for quarter in future.index:
        if quarter<pd.Period('2003Q3'):continue
        prior=training.loc[training.index<quarter] if quarter<=pd.Period('2019Q4') else training
        if len(prior)<40:raise ValueError('Insufficient training')
        x=prior.signal.to_numpy();y=prior.target.to_numpy();b=slope(x,y)
        predictor=training.loc[quarter,'signal'] if quarter in training.index else future.loc[quarter]
        mean=y.mean();variance=y.var(ddof=1)
        targets[quarter]=float(np.clip((mean+b*(predictor-x.mean()))/(5*variance),0,1))
        control[quarter]=float(np.clip(mean/(5*variance),0,1))
    return pd.Series(targets),pd.Series(control)


def simulate(prices,weights,dividends,lag=60,offset=1,bps=5,commission=1,sell_reserve=1,buyhold=False):
    cash=10000.;shares=0;pending=[];previous=10000.;records=[];trades=[]
    schedule={}
    for quarter,g in prices.groupby(prices.index.to_period('Q')):
        if quarter in weights.index and len(g)>offset:schedule[g.index[offset]]=weights.loc[quarter]
    if buyhold and schedule:schedule={min(schedule):1.}
    for date,bar in prices.iterrows():
        # Entitlement precedes ex-date trading; receivable is NAV, never buying power.
        entitled=shares*float(dividends.get(date,0.))
        if entitled:pending.append((date+pd.Timedelta(days=lag),entitled))
        paid=sum(amount for payable,amount in pending if payable<=date)
        cash+=paid;pending=[p for p in pending if p[0]>date]
        receivable=sum(amount for _,amount in pending)
        if date in schedule:
            weight=float(schedule[date]);assert 0<=weight<=1
            nav=cash+shares*bar.open+receivable
            desired=int(np.floor(weight*nav/bar.open));change=desired-shares
            if change>0:
                fill=bar.open*(1+bps/10000)
                affordable=max(0,int(np.floor((cash-commission)/fill)))
                qty=min(change,affordable)
                if qty:
                    cash-=qty*fill+commission;shares+=qty
                    trades.append({'date':str(date.date()),'side':'buy','quantity':qty,'fill':fill,'fees':commission})
            elif change<0:
                qty=-change;fill=bar.open*(1-bps/10000);fee=commission+sell_reserve
                cash+=qty*fill-fee;shares-=qty
                trades.append({'date':str(date.date()),'side':'sell','quantity':qty,'fill':fill,'fees':fee})
        equity=cash+shares*bar.close+receivable
        if cash<-1e-7 or shares<0 or equity<=0:raise ValueError('Invalid account state')
        records.append({'date':date,'equity':equity,'return':equity/previous-1,'cash':cash,'shares':shares,'receivable':receivable,'dividend_entitlement':entitled,'dividend_paid':paid})
        previous=equity
    return pd.DataFrame(records).set_index('date'),trades


def metrics(ret,years):
    equity=np.cumprod(1+ret,axis=-1);peak=np.maximum.accumulate(np.maximum(equity,1),axis=-1)
    return equity[...,-1]**(1/years)-1,(1-equity/peak).max(axis=-1)


def summarize(ledger,trades):
    years=(ledger.index[-1]-ledger.index[0]).days/365.25
    cg,dd=metrics(ledger['return'].to_numpy(),years)
    return {'net_cagr':float(cg),'daily_close_max_drawdown':float(dd),'ending_equity':float(ledger.equity.iloc[-1]),'fills':len(trades),
            'ending_cash':float(ledger.cash.iloc[-1]),'ending_shares':int(ledger.shares.iloc[-1]),'ending_receivable':float(ledger.receivable.iloc[-1])}


def bootstrap(strategy,control,block):
    f=pd.DataFrame({'strategy':strategy['return'],'control':control['return']})
    groups=[g.to_numpy().T for _,g in f.groupby(f.index.to_period('Q'))];n=len(groups);width=max(g.shape[1] for g in groups)
    padded=np.zeros((n,2,width))
    for i,g in enumerate(groups):padded[i,:,:g.shape[1]]=g
    rng=np.random.default_rng(118100+block);cagr=[];dd=[]
    for offset in range(0,10000,100):
        idx=stationary_indices(n,100,1/block,rng)
        sample=padded[idx].transpose(0,2,1,3).reshape(100,2,-1)
        c,d=metrics(sample,n/4);cagr.extend(c);dd.extend(d)
    cagr=np.asarray(cagr);dd=np.asarray(dd)
    return {'block_quarters':block,'paths':10000,'seed':118100+block,'cagr_advantage_ci95':np.quantile(cagr[:,0]-cagr[:,1],[.025,.975]).tolist(),
            'strategy_cagr_5_50_percentile':np.quantile(cagr[:,0],[.05,.5]).tolist(),'strategy_drawdown_95_percentile':float(np.quantile(dd[:,0],.95))}


def main():
    spec=json.loads((OUT/'registration.json').read_text())
    for name,digest in spec['hashes'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest
    freeze=json.loads((OUT/'analysis_freeze.json').read_text());assert freeze['code_sha256']==hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    assert not (OUT/'results.json').exists()
    full=pd.read_csv(INPUT/'SPY_1993_2023.csv',index_col='date',parse_dates=True)
    assert full.index.max()<pd.Timestamp('2024-01-01')
    events=json.loads((INPUT/'events.json').read_text());assert not events.get('splits',{})
    dividends={pd.Timestamp(v['date'],unit='s',tz='UTC').tz_convert('America/New_York').tz_localize(None).normalize():v['amount'] for v in events.get('dividends',{}).values()}
    old=pd.read_csv(BASE/'p118_audit/SPY_1993_2019.csv',index_col='date',parse_dates=True)
    training=panel(old,riskfree(BASE/'p52_audit/F-F_Research_Data_Factors_daily.CSV'))
    weights,controls=allocations(training,signals(full));prices=full.loc['2003-07-01':]
    strategy,trades=simulate(prices,weights,dividends);control,ct=simulate(prices,controls,dividends)
    fixed,ft=simulate(prices,pd.Series(.5,index=weights.index),dividends)
    buyhold,bt=simulate(prices,pd.Series(1.,index=weights.index),dividends,buyhold=True)
    stress,st=simulate(prices,weights,dividends,lag=120,offset=2,bps=10,commission=5)
    stress_control,sct=simulate(prices,controls,dividends,lag=120,offset=2,bps=10,commission=5)
    later=full.loc['2020-01-01':];ls,lt=simulate(later,weights,dividends);lc,lct=simulate(later,controls,dividends)
    summaries={name:summarize(ledger,t) for name,ledger,t in [('strategy',strategy,trades),('control',control,ct),('fixed50',fixed,ft),('buyhold',buyhold,bt),('stress',stress,st),('stress_control',stress_control,sct),('later_reset_strategy',ls,lt),('later_reset_control',lc,lct)]}
    intervals=[bootstrap(strategy,control,b) for b in (4,8,12)]
    passed=(summaries['strategy']['net_cagr']>0 and summaries['strategy']['net_cagr']>=summaries['control']['net_cagr']+.01 and all(r['cagr_advantage_ci95'][0]>0 for r in intervals)
            and summaries['later_reset_strategy']['net_cagr']>summaries['later_reset_control']['net_cagr'] and summaries['stress']['net_cagr']>summaries['stress_control']['net_cagr'])
    tiers={str(limit):bool(summaries['strategy']['daily_close_max_drawdown']<=limit and all(r['strategy_drawdown_95_percentile']<=limit for r in intervals)) for limit in (.5,.3,.2)}
    result={'type':'Raw-share execution screen with modeled dividend payment dates and open fills','summary':summaries,'bootstrap':intervals,'primary_gate_pass':bool(passed),'provisional_drawdown_compliance':tiers,
            'independent_confirmation':False,'trading_strategy_validated':False,'leaderboard_admission':False}
    strategy.to_csv(OUT/'strategy_ledger.csv');control.to_csv(OUT/'control_ledger.csv')
    (OUT/'results.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))


if __name__=='__main__':main()
