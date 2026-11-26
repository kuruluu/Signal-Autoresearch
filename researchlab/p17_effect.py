"""Fixed P17 contemporary share-volume/next-open mechanism test."""
import json,hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from .reality_check import stationary_indices

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'research/replication_first/p17_contemporary_001'


def assemble(prices):
    if not prices.index.is_unique or not prices.index.is_monotonic_increasing:raise ValueError('Invalid dates')
    if (prices.volume<=0).any():raise ValueError('Nonpositive volume')
    ret=prices.adj_close.pct_change(fill_method=None)
    logvol=np.log(prices.volume)
    volume=logvol-logvol.shift(1).rolling(252).mean()
    frame=pd.DataFrame({'return':ret,'volume':volume,'interaction':ret*volume,
                        'target':(prices.adj_close/prices.adj_open-1).shift(-1),
                        'target_date':pd.Series(prices.index,index=prices.index).shift(-1)})
    for day in range(5):frame[f'weekday{day}']=ret*(prices.index.dayofweek==day)
    return frame.dropna().loc['2008-01-01':]


def design(frame,candidate=True):
    cols=[f'weekday{d}' for d in range(5)]+(['interaction'] if candidate else [])
    return np.column_stack([np.ones(len(frame)),frame[cols].to_numpy()])


def expanding(frame):
    x=design(frame);y=frame.target.to_numpy();actual=[];pred=[];base=[]
    for i,date in enumerate(frame.target_date):
        if date<pd.Timestamp('2016-01-01'):continue
        # Row i-1's target is the previous session, complete before row i's open.
        candidate=np.linalg.lstsq(x[:i],y[:i],rcond=None)[0]
        control=np.linalg.lstsq(x[:i,:-1],y[:i],rcond=None)[0]
        pred.append(x[i]@candidate);base.append(x[i,:-1]@control);actual.append(y[i])
    mse=float(np.mean((np.asarray(actual)-pred)**2));baseline=float(np.mean((np.asarray(actual)-base)**2))
    return {'n':len(actual),'candidate_mse':mse,'baseline_mse':baseline,'mse_improvement':1-mse/baseline}


def main():
    from .reality_check import stationary_indices
    spec=json.loads((OUT/'registration.json').read_text())
    for path,digest in spec['hashes'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest
    freeze=json.loads((OUT/'analysis_freeze.json').read_text())
    assert hashlib.sha256(Path(__file__).read_bytes()).hexdigest()==freeze['code_sha256']
    assert not (OUT/'results.json').exists()
    prices=pd.read_csv(ROOT/'research/data/SPY.csv',index_col='date',parse_dates=True)
    assert prices.index.max()<pd.Timestamp('2024-01-01')
    frame=assemble(prices);x=design(frame);y=frame.target.to_numpy()
    coefficient=float(np.linalg.lstsq(x,y,rcond=None)[0][-1]);intervals=[]
    for block in (5,20,60):
        rng=np.random.default_rng(17000+block);draws=[]
        for offset in range(0,5000,50):
            indices=stationary_indices(len(frame),50,1/block,rng)
            draws.extend(np.linalg.lstsq(x[idx],y[idx],rcond=None)[0][-1] for idx in indices)
        intervals.append({'block_sessions':block,'paths':5000,'seed':17000+block,'ci95':np.quantile(draws,[.025,.975]).tolist()})
        print('Completed bootstrap block',block,flush=True)
    forecast=expanding(frame)
    result={'type':'Contemporary SPY volume proxy/next-open target; not native replication',
            'n':len(frame),'first_predictor_date':str(frame.index[0].date()),'last_target_date':str(frame.target_date.iloc[-1].date()),
            'interaction_coefficient':coefficient,'bootstrap':intervals,'forecast':forecast,
            'gate_pass':bool(coefficient<0 and all(r['ci95'][1]<0 for r in intervals) and forecast['mse_improvement']>0),
            'independent_confirmation':False,'trading_strategy_validated':False}
    (OUT/'results.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))


if __name__=='__main__':main()
