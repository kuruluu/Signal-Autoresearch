"""Calendar-only reconstruction of the February 2018 FOMC-cycle draft."""
from pathlib import Path
import json
import numpy as np
import pandas as pd

R = Path(__file__).resolve().parents[1]
B = R / 'research/replication_first/p126_audit'

def classify(days, meetings):
    days, meetings = pd.DatetimeIndex(days), pd.DatetimeIndex(meetings)
    if not meetings.is_monotonic_increasing or not meetings.is_unique or (meetings.dayofweek>4).any() or (days.dayofweek>4).any():
        raise ValueError('Expected sorted unique weekday meeting dates and weekday observations')
    anchors = meetings - pd.offsets.BDay(6)
    pos = anchors.searchsorted(days, side='right') - 1
    if (pos < 0).any(): raise ValueError('Missing preceding boundary meeting')
    if days.max() > meetings[-1]: raise ValueError('Missing following boundary meeting')
    offsets = np.busday_count(meetings.values[pos].astype('datetime64[D]'), days.values.astype('datetime64[D]'))
    return pd.DataFrame({'date':days,'meeting':meetings[pos],'offset':offsets,'week':(offsets+1)//5,'included':offsets<=33})

def main():
    # Pure synthetic boundaries: -6 resets, -1 remains week zero, holidays count.
    m=pd.to_datetime(['2016-01-06','2016-02-17','2016-03-30'])
    x=classify(pd.to_datetime(['2016-02-08','2016-02-09','2016-02-16','2016-02-17','2016-02-22','2016-02-23']),m)
    assert x.offset.tolist()==[23,-6,-1,0,3,4]
    assert x.meeting.iloc[1]==m[1] and x.week.iloc[1]==-1 and x.week.iloc[2]==0 and x.week.iloc[-1]==1
    s=json.loads((B/'completion.json').read_text())
    meetings=pd.to_datetime(['1993-12-21']+[v['date'] for v in s['rows']]+['2017-02-01'])
    out=classify(pd.bdate_range('1994-01-01','2016-12-31'),meetings)
    counts={str(k):int(v) for k,v in out[out.included].week.value_counts().sort_index().items()}
    assert len(out)==6000 and int(out.included.sum())==5997
    assert [counts[str(k)] for k in (0,2,4,6)]==[920,924,831,120]
    dropped=out.loc[~out.included,'date'].dt.strftime('%Y-%m-%d').tolist()
    assert dropped==['2004-06-21','2005-06-20','2005-06-21']
    result={'scope':'calendar only; no returns used','weekday_rows':len(out),'included_rows':int(out.included.sum()),'week_counts':counts,'dropped':dropped,'boundary_meetings':['1993-12-21','2017-02-01'],'synthetic_checks':'reset-minus6, premeeting-minus1, weekday count including holidays'}
    with (B/'quality_summary.json').open('x') as f: json.dump(result,f,indent=2)
    print(json.dumps(result,indent=2))

if __name__=='__main__': main()
