import argparse
import hashlib
import json
import platform
import time
from dataclasses import asdict
from pathlib import Path
import numpy as np
import pandas as pd
from .catalog import RESEARCH, ROOT
from .data import load_panel, protocol
from .signals import SIGNALS, raw_weights
from .engine import backtest, passive, metrics
from .bootstrap import inference

VARIANTS = [
 ('base', {}), ('hold2', {'hold':2}), ('hold10', {'hold':10}),
 ('cost2x', {'cost_multiplier':2}), ('cost4x', {'cost_multiplier':4}),
 ('delay1', {'delay':1}), ('miss10pct', {'miss':.1}),
 ('lookback80pct', {'multiplier':.8}), ('lookback120pct', {'multiplier':1.2}),
 ('equities_only', {'subset':['SPY','QQQ','IWM','EFA','EEM','XLF','XLE','XLK','XLV']}),
 ('defensive_only', {'subset':['TLT','IEF','GLD']})
]


def clean(value):
    if isinstance(value, dict):
        return {k: clean(v) for k,v in value.items()}
    if isinstance(value, (list,tuple)):
        return [clean(v) for v in value]
    if isinstance(value, np.ndarray):
        return clean(value.tolist())
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, (float,np.floating)):
        return float(value) if np.isfinite(value) else None
    return value


def save(path, value):
    Path(path).write_text(json.dumps(clean(value), indent=2, allow_nan=False), encoding='utf-8')


def freeze(pilot):
    p, fingerprint = protocol()
    specs = {'protocol_sha256': fingerprint, 'signals': [asdict(s) for s in SIGNALS],
             'variants': VARIANTS, 'numpy': np.__version__, 'pandas': pd.__version__, 'python': platform.python_version(),
             'code_sha256': {name:hashlib.sha256((ROOT/'researchlab'/name).read_bytes()).hexdigest()
                             for name in ['data.py','signals.py','engine.py','bootstrap.py','experiment.py']},
             'pilot': pilot, 'registered_before_this_run': time.time()}
    out = RESEARCH / ('pilot' if pilot else 'results')
    out.mkdir(exist_ok=True)
    prior = out / 'registration.json'
    if prior.exists():
        old = json.loads(prior.read_text())
        for key in ('protocol_sha256','signals','variants','code_sha256'):
            if old[key] != clean(specs[key]):
                raise ValueError('Registered experiment changed. Preserve old results and register a new output directory/version before rerunning.')
    else:
        save(prior, specs)
    return out


def run(pilot=False):
    out = freeze(pilot)
    panel, p = load_panel()
    chosen = [s for s in SIGNALS if not pilot or s.id in {'S01','S04','S14'}]
    variants = VARIANTS[:1] if pilot else VARIANTS
    # Common comparison starts after publication for ALL implemented primary papers.
    common_start = f'{max(s.available_year for s in SIGNALS)}-01-01'
    periods = {'validation': [max(common_start,p['validation'][0]),p['validation'][1]], 'walk_forward':p['walk_forward']}
    records, curves, active_matrices = [], {}, {}
    observed_file = RESEARCH / 'observed_periods.json'
    save(observed_file, {'development':'2007-2016 data inspected for warmup/engineering and retrospective own-sample tests',
        'validation':'2017-2020 used; common comparison 2019-2020', 'walk_forward':'2021-2023 used for research evaluation',
        'sealed_final':'2024-2025 NOT downloaded or evaluated', 'warning':'All viewed periods are now used; no rerun makes them untouched.'})
    for spec in chosen:
        print('Testing', spec.id, spec.name, flush=True)
        for variant, settings in variants:
            settings = dict(settings)
            raw = raw_weights(panel, spec, settings.pop('multiplier',1))
            experiment_id = spec.id + '__' + variant
            for period, (start,end) in periods.items():
                # A 10-session boundary gap; no positions/labels cross evaluation splits.
                eligible_dates = panel['adj_open'].loc[start:end].index
                start = eligible_dates[10]
                result = backtest(panel, raw, p, start, end, **settings)
                benchmark = passive(panel, start, end)
                stat = metrics(result, benchmark)
                stat.update({'experiment':experiment_id,'signal':spec.id,'variant':variant,'period':period,
                             'start':str(result.daily.index.min().date()),'end':str(result.daily.index.max().date()),
                             'papers':list(spec.papers),'family':spec.family,'adaptation':spec.adaptation})
                records.append(stat)
                active_matrices.setdefault(period, {})[experiment_id] = result.daily.net_return - benchmark
                if variant == 'base':
                    result.daily.to_csv(out / f'{spec.id}_{period}_daily.csv')
                    result.trades.to_csv(out / f'{spec.id}_{period}_trades.csv', index=False)
                    result.contribution.to_csv(out / f'{spec.id}_{period}_contributions.csv')
                    curves.setdefault(period,{})[spec.id] = result.daily.equity / p['capital']
                    rows = []
                    spy = panel['adj_close'].SPY
                    stress = spy.pct_change().rolling(60).std().shift(1) * np.sqrt(252) > .2
                    up = (spy > spy.rolling(200).mean()).shift(1).fillna(False).astype(bool)
                    for label, index in [('uptrend',up),('downtrend',~up),('high_vol',stress),('low_vol',~stress)]:
                        selected = result.daily.net_return.loc[index.reindex(result.daily.index).fillna(False)]
                        rows.append({'regime':label,'n':len(selected),'mean_net':selected.mean(),
                                     'mean_active':(selected-benchmark.loc[selected.index]).mean()})
                    save(out/f'{spec.id}_{period}_regimes.json', rows)
                    years = []
                    for year, sub in result.daily.groupby(result.daily.index.year):
                        years.append({'year':int(year),'net_total':np.prod(1+sub.net_return)-1,
                                      'active_mean':(sub.net_return-benchmark.loc[sub.index]).mean()})
                    stat['years'] = years
        if not pilot:
            own_start = max(p['development'][0],f'{spec.available_year}-01-01')
            own = backtest(panel, raw_weights(panel,spec),p,own_start,p['walk_forward'][1])
            m = metrics(own,passive(panel,own_start,p['walk_forward'][1]))
            m.update({'signal':spec.id,'start':own_start,'end':p['walk_forward'][1],
                      'label':'Post-publication available sample; overlaps used development/validation; not independent confirmation'})
            save(out/f'{spec.id}_own_sample.json',m)
    for period, columns in active_matrices.items():
        matrix = pd.DataFrame(columns)
        matrix.to_csv(out/f'{period}_active_all_variants.csv')
        print('Joint bootstrap',period,matrix.shape,flush=True)
        for block in [p['bootstrap_mean_block_sessions']] + ([] if pilot else p['bootstrap_block_sensitivity']):
            stats = inference(matrix.to_numpy(),p['bootstrap_replications'],block,p['seed'])
            for i, name in enumerate(matrix.columns):
                row = next(r for r in records if r['experiment']==name and r['period']==period)
                row[f'bootstrap_block_{block}'] = {key:values[i] for key,values in stats.items()}
        pd.DataFrame(curves[period]).to_csv(out/f'{period}_equity_curves.csv')
        pd.DataFrame({k:columns[k+'__base'] for k in curves[period]}).corr().to_csv(out/f'{period}_active_correlation.csv')
        start,end=periods[period]
        dates=panel['adj_open'].loc[start:end].index
        start=dates[10]
        save(out/f'{period}_benchmarks.json',{'equal_weight_total':np.prod(1+passive(panel,start,end))-1,
            'SPY_total':np.prod(1+passive(panel,start,end,['SPY']))-1,'cash_total':0,
            'note':'90% invested buy-and-hold with entry/exit costs; remaining 10% cash earns zero.'})
    save(out/'metrics.json', records)
    pd.DataFrame([{k:v for k,v in r.items() if not isinstance(v,(dict,list))} for r in records]).to_csv(out/'metrics.csv',index=False)
    save(out/'completion.json',{'completed':True,'experiments':len(chosen)*len(variants),'period_evaluations':len(records),
         'bootstrap_replications_per_matrix':p['bootstrap_replications'],'final_test_used':False})
    print('Completed:',out,flush=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--pilot',action='store_true')
    args=parser.parse_args()
    run(args.pilot)
