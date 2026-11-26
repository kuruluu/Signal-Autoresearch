"""Registered exploratory trend-versus-sizing experiment on already-used data."""
import argparse
import json
import time
import numpy as np
import pandas as pd
from .catalog import ROOT, RESEARCH
from .data import load_panel
from .engine import backtest, passive, metrics
from .experiment import save
from .bootstrap import inference
from .integrity import sha, verify

OUT=RESEARCH/'expansion_001'/'trend_experiment'
SPECS={
 'E01':('always','equal'), 'E02':('positive_return','equal'),
 'E03':('above_average','equal'), 'E04':('always','inverse_vol'),
 'E05':('positive_return','inverse_vol'), 'E06':('above_average','inverse_vol')}
PAIRS={'E02':'E01','E03':'E01','E05':'E04','E06':'E04'}
VARIANTS={'base':{},'hold2':{'hold':2},'hold10':{'hold':10},
          'cost2x':{'cost_multiplier':2},'cost4x':{'cost_multiplier':4},'delay1':{'delay':1}}

def weights(panel, direction, sizing):
    c=panel['adj_close']
    base=pd.DataFrame(.9/len(c.columns),index=c.index,columns=c.columns)
    if sizing=='inverse_vol':
        vol=c.pct_change(fill_method=None).ewm(com=60,min_periods=252,adjust=True).std()*np.sqrt(252)
        base=(base*.15/vol.replace(0,np.nan)).clip(upper=.2).fillna(0)
    elif sizing!='equal':
        raise ValueError(sizing)
    if direction=='positive_return':
        base*=c/c.shift(252)>1
    elif direction=='above_average':
        base*=c>c.rolling(252,min_periods=252).mean()
    elif direction!='always':
        raise ValueError(direction)
    return base.fillna(0)

def register():
    verify()
    OUT.mkdir(exist_ok=True,parents=True)
    definition={
      'id':'trend_followup_001','status':'exploratory on already-viewed history; no fresh validation',
      'question':'Does directional filtering add return over an always-long control with the same sizing rule and execution schedule?',
      'source_papers':['P01','P51','P52'],
      'definitions':SPECS,'paired_controls':PAIRS,'variants':VARIANTS,
      'lookback_sessions':252,'ewm_center_of_mass':60,'ewm_min_observations':252,
      'weight_definition':'Equal slots .9/12, or slots times .15 / past annual EWM volatility, capped .2. Negative/absent direction stays cash; no renormalization.',
      'risk_controls':'Original engine portfolio risk ceiling, caps, costs, liquidity filters apply unchanged to every arm.',
      'periods':{'used_2019_2020':['2019-01-01','2020-12-31'],'used_2021_2023':['2021-01-01','2023-12-31']},
      'boundary_gap_sessions':10,'bootstrap_paths':2000,'blocks':[10,20,40],'seed':6413,
      'multiple_testing':'Joint max-T of prior 231 primary comparisons, all 36 new primary comparisons and all 24 directional-minus-control contrasts; reserved-paper floor 100. Previously observed human choices are not corrected away.',
      'candidate_rule':'Base directional arm must have positive net CAGR and positive mean control difference in both used periods; 95% lower bound >0 and conservative p<=.05 for every block length; positive control difference at 2x and 4x costs in both periods; positive base control difference in >=2 of 3 later years. Only exploratory follow-up eligibility, never confirmed success.',
      'limitations':['Not a futures-paper replication','Long-only ETFs; 252 sessions approximate one year; total returns not excess returns',
        'Equal engine risk ceilings do not imply equal realized exposure or volatility; contrasts are not pure alpha',
        'EWM sample standard deviation is not the exact original exponentially weighted variance equation',
        'Observed through 2023; no parameter selection or final holdout use','Zero cash yield and fixed surviving universe remain'],
      'input_hashes':{str(p.relative_to(ROOT)):sha(p) for p in [RESEARCH/'protocol.json',RESEARCH/'data/manifest.json',RESEARCH/'expansion_001/candidates.json']},
      'code_hashes':{f:sha(ROOT/'researchlab'/f) for f in ['trend_followup.py','data.py','engine.py','bootstrap.py']}}
    path=OUT/'registration.json'
    if path.exists():
        old=json.loads(path.read_text())
        if old['definition']!=json.loads(json.dumps(definition)):
            raise ValueError('Frozen follow-up changed; use a new version, do not overwrite')
    else:
        save(path,{'registered_at_unix':time.time(),'definition':definition})
    return definition

def run():
    definition=register()
    panel,p=load_panel()
    rows=[];all_contrasts=[]
    for period,(start,end) in definition['periods'].items():
        start=panel['adj_open'].loc[start:end].index[10]
        benchmark=passive(panel,start,end)
        new={}
        for arm,(direction,sizing) in SPECS.items():
            raw=weights(panel,direction,sizing)
            for variant,settings in VARIANTS.items():
                name=f'{arm}__{variant}'
                result=backtest(panel,raw,p,start,end,**settings)
                new[name]=result.daily.net_return
                m=metrics(result,benchmark)
                m.update(arm=arm,variant=variant,period=period,direction=direction,sizing=sizing)
                rows.append(m)
                if variant=='base':
                    result.daily.to_csv(OUT/f'{arm}_{period}_daily.csv')
                    result.trades.to_csv(OUT/f'{arm}_{period}_trades.csv',index=False)
            print(period,arm,flush=True)
        net=pd.DataFrame(new)
        net.to_csv(OUT/f'{period}_net_all_variants.csv')
        contrasts={f'{a}_minus_{control}__{v}':net[f'{a}__{v}']-net[f'{control}__{v}']
                   for a,control in PAIRS.items() for v in VARIANTS}
        delta=pd.DataFrame(contrasts)
        delta.to_csv(OUT/f'{period}_control_differences.csv')
        original='validation' if period=='used_2019_2020' else 'walk_forward'
        prior=pd.read_csv(RESEARCH/'results'/f'{original}_active_all_variants.csv',index_col=0,parse_dates=True)
        if not prior.index.equals(net.index):
            raise ValueError('Misaligned prior and new comparison dates')
        joint=pd.concat([prior,net.sub(benchmark,axis=0),delta],axis=1)
        joint.to_csv(OUT/f'{period}_joint_family.csv')
        stats={}
        print('Bootstrap',period,joint.shape,flush=True)
        for block in definition['blocks']:
            result=inference(joint.to_numpy(),2000,block,6413,reserved_papers=100)
            stats[block]={name:{key:values[i] for key,values in result.items()} for i,name in enumerate(joint)}
        save(OUT/f'{period}_inference.json',stats)
        for name in delta:
            arm,rest=name.split('_minus_');control,variant=rest.split('__')
            all_contrasts.append({'arm':arm,'control':control,'variant':variant,'period':period,
                'mean_difference_annualized':delta[name].mean()*252,
                'years':{str(y):s.mean()*252 for y,s in delta[name].groupby(delta.index.year)},
                'bootstrap':{str(b):stats[b][name] for b in stats}})
    save(OUT/'metrics.json',rows)
    pd.DataFrame(rows).to_csv(OUT/'metrics.csv',index=False)
    save(OUT/'contrasts.json',all_contrasts)
    findings=[]
    for arm in PAIRS:
        bases=[r for r in all_contrasts if r['arm']==arm and r['variant']=='base']
        stresses=[r for r in all_contrasts if r['arm']==arm and r['variant'] in ('cost2x','cost4x')]
        later=next(r for r in bases if r['period']=='used_2021_2023')
        checks={
          'positive_net_both':all(r['net_cagr']>0 for r in rows if r['arm']==arm and r['variant']=='base'),
          'positive_control_difference_both':all(r['mean_difference_annualized']>0 for r in bases),
          'positive_lower_bound_all_blocks_both':all(s['low_daily']>0 for r in bases for s in r['bootstrap'].values()),
          'adjusted_significance_all_blocks_both':all(s['p_conservative']<=.05 for r in bases for s in r['bootstrap'].values()),
          'higher_costs_both':all(r['mean_difference_annualized']>0 for r in stresses),
          'two_of_three_later_years':sum(v>0 for v in later['years'].values())>=2}
        findings.append({'arm':arm,'checks':checks,'exploratory_eligible':all(checks.values()),'confirmed':False})
    save(OUT/'assessment.json',findings)
    save(OUT/'completion.json',{'completed':True,'new_portfolio_variants':36,'period_evaluations':72,
         'paired_contrasts':24,'joint_tests_per_period':291,'bootstrap_paths_per_block':2000,
         'final_used':False,'exploratory_eligible':sum(r['exploratory_eligible'] for r in findings)})
    verify()
    print('Finished exploratory follow-up',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--register-only',action='store_true')
    args=parser.parse_args()
    if args.register_only: register()
    else: run()
