"""Fixed historical-beta liquidity premium check, distinct from predicted betas."""
import json, hashlib, datetime
from pathlib import Path
import numpy as np
from .reality_check import stationary_indices

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'research/replication_first'
OUT=BASE/'p19_historical_001'
INPUTS=[BASE/'p19_audit'/n for n in ('liq_data_1962_2022.txt','liq_vw_hist_deciles_1968_2022.txt')]

def load():
    factors=np.loadtxt(INPUTS[0],comments='%')
    deciles=np.loadtxt(INPUTS[1],comments='%')
    dates=factors[:,0].astype(int)
    expected=np.array([y*100+m for y in range(1962,2023) for m in range(1,13) if y*100+m>=196208])
    if not np.array_equal(dates,expected) or factors.shape!=(725,4):raise ValueError('Unexpected factor coverage')
    keep=dates>=196801
    if deciles.shape!=(660,11) or not np.isfinite(deciles).all():raise ValueError('Invalid decile panel')
    spread=deciles[:,9]-deciles[:,0]
    if not np.allclose(spread,deciles[:,10],atol=2e-8,rtol=0):raise ValueError('Decile spread mismatch')
    if not np.allclose(spread,factors[keep,3],atol=2e-8,rtol=0):raise ValueError('Factor/date alignment mismatch')
    return dates[keep],spread

def register():
    OUT.mkdir(exist_ok=True)
    spec={'id':'P19_historical_001','registered_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'estimand':'Annualized arithmetic mean of author value-weighted historical-liquidity-beta decile10 minus decile1 monthly returns. No subtraction of RF for zero-investment spread.',
          'windows':{'original_period_partial':[196801,199912],'later_persistence':[200301,202212]},
          'excluded_gap':'2000-2002 omitted to separate later window from 2002 manuscript preparation; not a fitted choice.',
          'inference':'10000 stationary bootstrap paths per window, expected block lengths3/12/24 months, fixed seeds190000+window_index*100+block. Two-sided95% percentile intervals of annual arithmetic mean. Joint advancement gate: both windows mean>0 and all six lower bounds>0. No numerical comparison to predicted-beta headline7.5%; no alternate decile or endpoint search.',
          'limitations':'Author revised2022 construction, not untouched holdout; no predicted-beta replication, factor-adjusted alpha, stock holdings/costs/borrow reconstruction, compounded account return, or validated strategy. Constant sorted portfolio returns bootstrap is conditional, not a reestimated stock-universe simulation. Passing only permits execution feasibility audit.',
          'hashes':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),ROOT/'researchlab/reality_check.py',*INPUTS]}}
    with (OUT/'registration.json').open('x') as f:json.dump(spec,f,indent=2)

def main():
    spec=json.loads((OUT/'registration.json').read_text())
    for name,digest in spec['hashes'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:raise ValueError('Frozen input/code changed')
    if (OUT/'results.json').exists():raise ValueError('Results already exist')
    dates,spread=load();results={}
    for i,(name,(start,end)) in enumerate(spec['windows'].items()):
        x=spread[(dates>=start)&(dates<=end)];intervals=[]
        for block in (3,12,24):
            seed=190000+i*100+block
            idx=stationary_indices(len(x),10000,1/block,np.random.default_rng(seed))
            intervals.append({'block_months':block,'seed':seed,'paths':10000,'annual_mean_ci95':np.quantile(x[idx].mean(1)*12,[.025,.975]).tolist()})
        results[name]={'n_months':len(x),'annual_arithmetic_mean':float(x.mean()*12),'annual_volatility':float(x.std(ddof=1)*np.sqrt(12)),'bootstrap':intervals,'gate_pass':bool(x.mean()>0 and all(r['annual_mean_ci95'][0]>0 for r in intervals))}
    result={'windows':results,'advance_to_execution_audit':all(v['gate_pass'] for v in results.values()),'predicted_beta_headline_replicated':False,'strategy_validated':False,'independent_confirmation':False}
    with (OUT/'results.json').open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    import sys
    register() if '--register' in sys.argv else main()
