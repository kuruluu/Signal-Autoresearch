"""Fixed turn-of-month reconstruction; historical calendar sessions, no filling."""
import json,hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from .reality_check import stationary_indices

BASE=Path(__file__).resolve().parents[1]/'research/replication_first'
OUT=BASE/'p117_partial_001'


def months(price,start,end):
    returns=price.pct_change(fill_method=None).loc[start:end]
    groups={p:g for p,g in returns.groupby(returns.index.to_period('M'))}
    rows=[]
    first=pd.Timestamp(start).to_period('M');last=pd.Timestamp(end).to_period('M')
    for period,g in groups.items():
        prev=groups.get(period-1)
        if period<=first or period>=last or prev is None or len(g)<5:continue
        values=np.array([prev.iloc[-1],*g.iloc[:3]])
        rest=g.iloc[3:-1]
        if not np.isfinite(values).all() or not np.isfinite(rest).all():raise ValueError('Invalid returns')
        rows.append({'month':str(period),'minus1':values[0],'plus1':values[1],
                     'plus2':values[2],'plus3':values[3],
                     'tom_sum':values.sum(),'rest_sum':rest.sum(),'rest_n':len(rest)})
    return pd.DataFrame(rows)


def bootstrap(frame,block):
    a=frame[['tom_sum','rest_sum','rest_n']].to_numpy();rng=np.random.default_rng(117000+block)
    means=[];contrasts=[]
    for _ in range(100):
        idx=stationary_indices(len(a),100,1/block,rng)
        sampled=a[idx];mean=sampled[:,:,0].mean(axis=1)
        contrast=mean-4*sampled[:,:,1].sum(axis=1)/sampled[:,:,2].sum(axis=1)
        means.extend(mean);contrasts.extend(contrast)
    return {'block_months':block,'paths':10000,'seed':117000+block,
            'mean_ci95_percent':(100*np.quantile(means,[.025,.975])).tolist(),
            'contrast_ci95_percent':(100*np.quantile(contrasts,[.025,.975])).tolist()}


def main():
    spec=json.loads((OUT/'registration.json').read_text());path=BASE/'p50_audit/DJIA.csv'
    assert hashlib.sha256(path.read_bytes()).hexdigest()==spec['input_sha256']
    f=pd.read_csv(path,index_col=0,parse_dates=True);price=f.value
    assert price.index.is_unique and price.index.is_monotonic_increasing and (price>0).all()
    frame=months(price,'1897-01-04','1986-06-11')
    columns=['minus1','plus1','plus2','plus3'];means=100*frame[columns].mean()
    target=np.array([.122,.084,.127,.140]);total=float(means.sum())
    numerical=bool((np.abs(means.to_numpy()-target)<=.03).all() and abs(total-.473)<=.08)
    intervals=[bootstrap(frame,b) for b in (3,12,24)]
    contrast=100*(frame.tom_sum.mean()-4*frame.rest_sum.sum()/frame.rest_n.sum())
    result={'type':'Partial native-period reconstruction; third-party index vintage',
            'n_months':len(frame),'published_n_each':1052,'count_matches':len(frame)==1052,
            'position_means_percent':means.to_dict(),'four_day_sum_mean_percent':total,
            'contrast_percent':float(contrast),'numerical_gate_pass':numerical,'bootstrap':intervals,
            'advance_to_separately_registered_later_test':numerical and all(r['contrast_ci95_percent'][0]>0 for r in intervals),
            'exact_replication':False,'trading_strategy_validated':False,
            'boundary_policy':'Group by receiving month. Omit first/last sample months and months without preceding recorded calendar month. Non-TOM baseline days4 through penultimate of receiving month, resampled jointly with that month TOM vector.',
            'splits':{label:{'n':len(g),'sum_mean_percent':float(100*g.tom_sum.mean())} for label,g in [('before_June1952',frame[frame.month<'1952-06']),('June1952_onward',frame[frame.month>='1952-06'])]}}
    (OUT/'results.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))


if __name__=='__main__':main()
