"""Frozen 50-session IWM transfer; exploratory, not independent confirmation."""
import argparse
import json
from datetime import datetime, timezone
import numpy as np
import pandas as pd
from .p52_reproduction import ROOT, INPUT, digest, daily_table, signals, strategy_returns, bootstrap
from .p24_bridge import simulate

OUT=ROOT/'research/replication_first/p52_iwm_bridge_001'


def close_positions(prices, n=50):
    valid=prices.shift(n).notna()
    return pd.DataFrame({'MA':prices.gt(prices.rolling(n).mean()).where(valid),
                         'TSMOM':prices.gt(prices.shift(n)).where(valid)})


def execution_inputs(frame, rf, start, end):
    positions=close_positions(frame.adj_close).shift(1).loc[start:end].astype(float)
    risky=(frame.adj_open.shift(-1)/frame.adj_open-1).reindex(positions.index)
    cash=rf.reindex(positions.index)
    if positions.isna().any().any() or risky.isna().any() or cash.isna().any():
        raise ValueError('Missing signal, next open or cash return')
    return positions,risky,cash


def monthly(frame):
    series=frame.net_return.copy()
    series.index=pd.DatetimeIndex(series.index)
    return (1+series).groupby(series.index.to_period('M')).prod()-1


def register():
    files=[ROOT/'research/data/IWM.csv',ROOT/'research/data/exchange_schedule.csv',
        INPUT/'Portfolios_Formed_on_ME_daily.CSV',INPUT/'F-F_Research_Data_Factors_daily.CSV',
        ROOT/'researchlab/p52_reproduction.py',ROOT/'researchlab/p24_bridge.py']
    spec=dict(id='p52_iwm_bridge_001',parent='P52_partial_001',
        status='Development transfer and economic feasibility, no independent confirmation',
        window=50,calibration=['2008-01-01','2010-12-31'],evaluation=['2011-01-01','2019-12-31'],months=108,
        sequence=['Matched-period French Q1 gross MA versus TSMOM',
                  'Same-period IWM gross close-to-close rules',
                  'IWM previous-close signal executed next session open, with costs'],
        instrument_difference='IWM Russell 2000 ETF is not the French NYSE-breakpoint smallest quintile; universe, fund costs and data source change jointly',
        signal='Long if adjusted close exceeds current-inclusive SMA50; TSMOM long if close exceeds close 50 sessions ago; otherwise cash; no shorts/leverage',
        execution='Previous session close controls entry at current open; hold to next session open. Synthetic adjusted units. Include initial entry and final liquidation costs. Monthly returns grouped by entry date, so month-end overnight belongs to entry month.',
        cash='French daily RF on entry session as realized open-to-open cash approximation; not a decision feature',
        costs_bps_per_side=[5,10,20],
        cost_model='All-in proportional adverse execution cost on net traded notional, self financed. Scenario assumptions, not measured historical spreads; no separate double-counted commission.',
        controls=['TSMOM50 with identical execution', 'Daily rebalanced constant IWM fraction equal to MA average lagged entry weight in 2008-2010; rest cash', 'Fully invested IWM context'],
        objective='Incremental net arithmetic mean monthly return over TSMOM and past-calibrated exposure control, annualized by 12',
        gate='At 5 bps, both primary contrasts >=1 percentage point/year, each lower 95% bootstrap bound positive and Holm p<=.05 for all blocks. Both contrasts positive at 10 and 20 bps. Otherwise fails registered usefulness gate; uncertainty remains explicit.',
        inference='Joint stationary bootstrap of six monthly paired differences (two controls times three costs); Holm over all six separately at each block 6/12/24 months; 5000 paths seed52101. Escalate all blocks to 20000 if any base primary adjusted p in [.04,.06]. Conditional on frozen calibration and fixed rule histories; not fitting-aware model selection inference.',
        secondary='CAGR, drawdown sampled at opens, average exposure and costs; cannot replace failed primary objective',
        assumptions=['Previously observed history is development evidence','Adjusted prices are revised synthetic units, not historical quotes',
          'No capacity/partial fill/borrow simulation; daily data cannot establish precise fills',
          'Past-calibrated exposure control need not match realized test exposure or risk',
          'Gross close-to-close diagnostic is theoretical; next-open stage is the executable approximation'],
        sealed_access=False,input_code_hashes={str(f):digest(f) for f in files},code_hash=digest(__file__))
    OUT.mkdir(exist_ok=True)
    f=OUT/'registration.json'
    if f.exists():
        old=json.loads(f.read_text());assert {k:v for k,v in old.items() if k!='registered_at_utc'}==spec,'Frozen registration changed'
        return old
    spec['registered_at_utc']=datetime.now(timezone.utc).isoformat();f.write_text(json.dumps(spec,indent=2))
    return spec


def run():
    assert (OUT/'registration.json').exists(),'Register before evaluation'
    spec=register();assert not (OUT/'results.json').exists(),'Do not overwrite results'
    f=pd.read_csv(ROOT/'research/data/IWM.csv',index_col='date',parse_dates=True)
    assert f.index.is_unique and f.index.is_monotonic_increasing and f.index.max()<pd.Timestamp('2024-01-01')
    rf=daily_table(INPUT/'F-F_Research_Data_Factors_daily.CSV').RF
    q=daily_table(INPUT/'Portfolios_Formed_on_ME_daily.CSV','Value Weighted Returns -- Daily')[['Lo 20']]
    diagnostic={}
    for name,r in [('French_Q1',q),('IWM',f.adj_close.pct_change().dropna().to_frame('IWM'))]:
        r=r.loc['2007':'2019'];cash=rf.reindex(r.index);assert not cash.isna().any()
        a,b,_,_=signals(r)
        out=[]
        for pos in [a,b]:
            daily=strategy_returns(r,cash,pos).loc['2011':'2019'];assert not daily.isna().any().any()
            m=(1+daily).groupby(daily.index.to_period('M')).prod()-1;out.append(float(m.iloc[:,0].mean()*1200))
        diagnostic[name]={'MA_annualized_mean_pct':out[0],'TSMOM_annualized_mean_pct':out[1],'difference_pp_year':out[0]-out[1]}
    calibration=close_positions(f.adj_close).shift(1).loc['2008':'2010'].MA.astype(float)
    assert not calibration.isna().any();control=float(calibration.mean())
    positions,risky,cash=execution_inputs(f,rf,'2011-01-01','2019-12-31')
    contrasts=[];labels=[];stats={}
    for cost in spec['costs_bps_per_side']:
        rules={'MA':positions.MA,'TSMOM':positions.TSMOM,'exposure_control':positions.MA*0+control,'market':positions.MA*0+1}
        output={key:simulate(w,risky,cash,cost/10000) for key,w in rules.items()}
        m={key:monthly(v) for key,v in output.items()}
        assert all(len(v)==108 for v in m.values())
        for key,v in output.items():
            v.to_csv(OUT/f'{key}_{cost}bps_daily.csv')
            stats[f'{key}_{cost}bps']=dict(cagr=float(v.equity.iloc[-1]**(12/108)-1),
                annualized_mean_pct=float(m[key].mean()*1200),mean_entry_weight=float(rules[key].mean()),
                open_sampled_max_drawdown=float((v.equity/v.equity.cummax().clip(lower=1)-1).min()),
                summed_fee_fraction=float(v.cost_fraction.sum()))
        for key in ['TSMOM','exposure_control']:
            contrasts.append((m['MA']-m[key]).to_numpy());labels.append(f'{cost}bps_MA_minus_{key}')
    values=np.column_stack(contrasts)
    inf=[bootstrap(values,b,seed=52101) for b in [6,12,24]]
    if any(.04<=x['holm_p'][j]<=.06 for x in inf for j in [0,1]):inf=[bootstrap(values,b,paths=20000,seed=52101) for b in [6,12,24]]
    means=values.mean(axis=0)*1200
    checks=dict(base_minimum=bool((means[:2]>=1).all()),
        base_uncertainty=all(x['percentile_95_monthly_pp'][j][0]>0 and x['holm_p'][j]<=.05 for x in inf for j in [0,1]),
        cost_stress_positive=bool((means[2:]>0).all()))
    result=dict(verdict='Meets development usefulness gate' if all(checks.values()) else 'Fails registered usefulness gate',
        checks=checks,diagnostics=diagnostic,calibrated_exposure_control=control,summary=stats,
        contrast_labels=labels,annualized_contrast_pp=means.tolist(),bootstrap=inf,independently_confirmed=False)
    (OUT/'results.json').write_text(json.dumps(result,indent=2))
    (OUT/'completion.json').write_text(json.dumps(dict(completed_at_utc=datetime.now(timezone.utc).isoformat(),hashes={x.name:digest(x) for x in OUT.iterdir() if x.is_file()}),indent=2))
    print(json.dumps({k:v for k,v in result.items() if k not in ['bootstrap','summary']},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');args=p.parse_args()
    if args.run:run()
    else:register();print('Registered P52 IWM bridge; no strategy outcomes calculated.')
