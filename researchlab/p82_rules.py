"""Explicit BLL26 reconstruction; fixed-position semantics disclosed separately."""
import numpy as np
import pandas as pd

PAIRS=[(1,50),(1,150),(5,150),(1,200),(2,200)]


def fixed_hold(events,days=10):
    """An event at close t controls next days returns; ignore intervening events."""
    events=np.asarray(events,int);out=np.zeros(len(events),int);remaining=0;position=0
    for i,event in enumerate(events):
        if remaining==0:
            position=int(event);remaining=days if event else 0
        out[i]=position
        if remaining:remaining-=1
    return out


def positions(price):
    p=pd.Series(price).astype(float)
    if not p.notna().all() or (p<=0).any():raise ValueError('Invalid prices')
    columns={}
    for fast,slow in PAIRS:
        short=p.rolling(fast).mean();long=p.rolling(slow).mean()
        for band in [0,.01]:
            state=np.where(short>long*(1+band),1,np.where(short<long*(1-band),-1,0))
            columns[f'VMA_{fast}_{slow}_{band}']=state
            # Entry into a band-exceeding state is treated as a crossover event.
            previous=np.r_[0,state[:-1]];events=np.where((state!=0)&(state!=previous),state,0)
            columns[f'FMA_{fast}_{slow}_{band}']=fixed_hold(events)
    for slow in [50,150,200]:
        high=p.shift(1).rolling(slow).max();low=p.shift(1).rolling(slow).min()
        for band in [0,.01]:
            events=np.where(p>high*(1+band),1,np.where(p<low*(1-band),-1,0))
            columns[f'TRB_{slow}_{band}']=fixed_hold(events)
    result=pd.DataFrame(columns,index=p.index)
    assert result.shape[1]==26
    return result
