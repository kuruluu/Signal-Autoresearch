"""Fixed calendar-aware minute boundary extraction; never fills missing prices."""
import gzip,json,hashlib
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'research/replication_first/p40_contemporary_002'


def extract(bars,calendar,prior_close=None):
    frame=bars.copy()
    if not isinstance(frame.index,pd.DatetimeIndex) or frame.index.tz is None:
        raise ValueError('Timezone-aware timestamps required')
    frame.index=frame.index.tz_convert('America/New_York')
    grouped={str(day):group.sort_index() for day,group in frame.groupby(frame.index.date)}
    features=[];audit=[]
    for day in calendar:
        date=day['date'];opening=pd.Timestamp(date+' '+day['open'],tz='America/New_York')
        closing=pd.Timestamp(date+' '+day['close'],tz='America/New_York')
        group=grouped.get(date,frame.iloc[:0]);regular=group[(group.index>=opening)&(group.index<closing)]
        expected=pd.date_range(opening,closing-pd.Timedelta(minutes=1),freq='min')
        full_session=day['open']=='09:30' and day['close']=='16:00'
        duplicate=regular.index.duplicated().any()
        complete=(not duplicate and regular.index.equals(expected))
        valid_prices=(np.isfinite(regular[['o','c']].to_numpy()).all() and (regular[['o','c']]>0).all().all())
        status='eligible'
        if not full_session:status='nonstandard_session'
        elif duplicate:status='duplicate_timestamp'
        elif not complete:status='missing_minutes'
        elif not valid_prices:status='invalid_price'
        elif prior_close is None:status='missing_previous_close'
        if status=='eligible':
            first=regular.loc[pd.Timestamp(date+' 09:59',tz='America/New_York'),'c']
            entry=regular.loc[pd.Timestamp(date+' 15:30',tz='America/New_York'),'o']
            last=regular.loc[pd.Timestamp(date+' 15:59',tz='America/New_York'),'c']
            features.append({'date':date,'first_half_return':float(first/prior_close-1),
                             'last_half_return':float(last/entry-1)})
        audit.append({'date':date,'status':status,'regular_minutes':len(regular),
                      'expected_minutes':len(expected),'full_session':full_session})
        # A half-day can supply the previous session close. A missing close cannot.
        endpoint=regular.loc[regular.index==expected[-1],'c']
        prior_close=float(endpoint.iloc[0]) if len(endpoint)==1 and np.isfinite(endpoint.iloc[0]) and endpoint.iloc[0]>0 else None
    return features,audit,prior_close


def build():
    calendar=json.loads((OUT/'calendar.json').read_text());rows=[];audits=[];prior=None
    manifests=json.loads((OUT/'input_manifest.json').read_text())
    assert [x['year'] for x in manifests]==list(range(2016,2024))
    for record in manifests:
        year=record['year'];path=OUT/f'SPY_{year}_sip_1min.json.gz'
        assert hashlib.sha256(path.read_bytes()).hexdigest()==record['sha256']
        with gzip.open(path,'rt',encoding='utf-8') as f:bars=pd.DataFrame(json.load(f))
        bars.index=pd.to_datetime(bars.pop('t'),utc=True)
        assert (bars.index.year==year).all()
        subset=[d for d in calendar if d['date'].startswith(str(year))]
        features,audit,prior=extract(bars,subset,prior)
        rows.extend(features);audits.extend(audit)
    pd.DataFrame(rows).to_csv(OUT/'features.csv',index=False)
    pd.DataFrame(audits).to_csv(OUT/'session_audit.csv',index=False)
    full=[d for d in audits if d['full_session']]
    quality={'eligible_rows':len(rows),'full_sessions':len(full),
             'coverage':len(rows)/len(full),'status_counts':pd.Series([d['status'] for d in audits]).value_counts().to_dict(),
             'quality_gate':len(rows)/len(full)>=.95,
             'feature_code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
             'note':'Coverage only; no effect estimates computed. Missing first previous close is included conservatively in denominator.'}
    (OUT/'quality_summary.json').write_text(json.dumps(quality,indent=2))
    print(json.dumps(quality,indent=2))


if __name__=='__main__':build()
