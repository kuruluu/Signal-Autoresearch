"""Fixed original-period BTC weekly momentum provider-transfer check."""
import json,hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from .reality_check import stationary_indices

ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'research/replication_first';OUT=BASE/'p119_partial_001'


def weekly(price):
    if not price.index.is_unique or not price.index.is_monotonic_increasing:raise ValueError('Invalid dates')
    if not np.isfinite(price).all() or (price<=0).any():raise ValueError('Invalid prices')
    expected=pd.date_range(price.index[0],price.index[-1],freq='D')
    if not price.index.equals(expected):raise ValueError('Missing calendar day; no imputation')
    sundays=price.loc[price.index.dayofweek==6]
    returns=sundays.pct_change(fill_method=None).dropna()
    frame=pd.DataFrame({'signal':returns,'target':returns.shift(-1),
                        'target_date':pd.Series(returns.index,index=returns.index).shift(-1)}).dropna()
    return returns,frame


def slope(x,y):
    xc=x-x.mean(axis=-1,keepdims=True);yc=y-y.mean(axis=-1,keepdims=True)
    return (xc*yc).sum(axis=-1)/(xc*xc).sum(axis=-1)


def expanding(frame,initial=104):
    x=frame.signal.to_numpy();y=frame.target.to_numpy();pred=[];base=[]
    for i in range(initial,len(frame)):
        b=slope(x[:i],y[:i]);pred.append(y[:i].mean()+b*(x[i]-x[:i].mean()));base.append(y[:i].mean())
    mse=float(np.mean((y[initial:]-pred)**2));benchmark=float(np.mean((y[initial:]-base)**2))
    return {'n':len(pred),'model_mse':mse,'mean_mse':benchmark,'mse_improvement':1-mse/benchmark}


def main():
    spec=json.loads((OUT/'registration.json').read_text())
    for name,digest in spec['hashes'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest
    freeze=json.loads((OUT/'analysis_freeze.json').read_text());assert freeze['code_sha256']==hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    assert not (OUT/'results.json').exists()
    data=json.loads((BASE/'p119_audit/coinmetrics_btc_2011_2018.json').read_text())
    price=pd.Series([float(x['PriceUSD']) for x in data],index=pd.to_datetime([x['time'] for x in data],utc=True).tz_localize(None))
    assert price.index[0]==pd.Timestamp('2011-01-01') and price.index[-1]==pd.Timestamp('2018-05-31')
    returns,frame=weekly(price);x=frame.signal.to_numpy();y=frame.target.to_numpy();b=float(slope(x,y));a=float(y.mean()-b*x.mean())
    r2=float(1-np.sum((y-a-b*x)**2)/np.sum((y-y.mean())**2));intervals=[]
    for block in (4,12,26):
        idx=stationary_indices(len(frame),10000,1/block,np.random.default_rng(119000+block));draws=slope(x[idx],y[idx])
        intervals.append({'block_weeks':block,'paths':10000,'seed':119000+block,'slope_ci95':np.quantile(draws,[.025,.975]).tolist()})
    forecast=expanding(frame);mean=float(returns.mean());sd=float(returns.std(ddof=1))
    numerical=abs(b-.19)<=.08 and abs(mean-.0379)<=.01 and abs(sd-.1664)<=.02
    result={'type':'BTC original-period weekly momentum provider-transfer partial test','daily_rows':len(price),'weekly_returns':len(returns),'regression_rows':len(frame),
            'target_first':str(frame.target_date.iloc[0].date()),'target_last':str(frame.target_date.iloc[-1].date()),
            'weekly_mean_percent':100*mean,'weekly_sd_percent':100*sd,'slope':b,'r_squared':r2,
            'numerical_gate_pass':bool(numerical),'bootstrap':intervals,'expanding_forecast':forecast,
            'gate_pass':bool(numerical and b>0 and all(r['slope_ci95'][0]>0 for r in intervals) and forecast['mse_improvement']>0),
            'independent_confirmation':False,'trading_strategy_validated':False}
    (OUT/'results.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))


if __name__=='__main__':main()
