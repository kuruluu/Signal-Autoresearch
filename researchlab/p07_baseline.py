"""Native author momentum-decile validation and fixed Table1 baseline."""
import json,hashlib
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'research/replication_first'
OUT=BASE/'p07_baseline_001'


def portfolios(path,monthly=False):
    f=pd.read_csv(path,sep=r'\s+',header=None,names=['date','decile','return','market_equity','firms'])
    f['date']=pd.to_datetime(f.date.astype(str),format='%Y%m%d')
    if f.duplicated(['date','decile']).any():raise ValueError('Duplicate date/decile')
    if not f.groupby('date').decile.apply(lambda x:set(x)==set(range(1,11))).all():raise ValueError('Missing/invalid deciles')
    if not np.isfinite(f[['return','market_equity','firms']]).all().all():raise ValueError('Nonfinite data')
    if (f['return']<-1).any() or (f.market_equity<=0).any() or (f.firms<1).any():raise ValueError('Invalid portfolio values')
    panel=f.pivot(index='date',columns='decile',values='return').sort_index()
    if monthly:
        periods=panel.index.to_period('M')
        if periods.duplicated().any():raise ValueError('Duplicate months')
        if not periods.equals(pd.period_range('1927-01','2013-03',freq='M')):raise ValueError('Unexpected monthly coverage')
    return panel


def main():
    spec=json.loads((OUT/'registration.json').read_text())
    for path,digest in spec['hashes'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest
    freeze=json.loads((OUT/'analysis_freeze.json').read_text());assert freeze['code_sha256']==hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    assert not (OUT/'results.json').exists()
    month=portfolios(BASE/'p07_audit/m_m_pt_tot.txt',True);daily=portfolios(BASE/'p07_audit/d_m_pt_tot.txt')
    assert daily.index.min()==pd.Timestamp('1927-01-03') and daily.index.max()==pd.Timestamp('2013-03-28')
    wml=month[10]-month[1];mean=float(1200*wml.mean());sd=float(np.sqrt(12)*100*wml.std(ddof=1));sr=mean/sd
    result={'type':'Native author portfolio input/Table1 verification only','monthly_rows':len(month),'daily_rows':len(daily),
            'annual_mean_percent':mean,'annual_sd_percent':sd,'sharpe':sr,
            'baseline_gate_pass':abs(mean-17.9)<=.15 and abs(sd-30)<=.15 and abs(sr-.6)<=.015,
            'narrative_discrepancy':'Fixed printedTable1SR.60 primary; narrative.71 not used for retuning',
            'crash_mechanism_tested':False,'trading_strategy_validated':False}
    (OUT/'results.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))


if __name__=='__main__':main()
