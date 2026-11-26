"""Registered partial Table3 optionality mechanism, not a trading forecast."""
import re,json,hashlib
from datetime import datetime,timezone
from pathlib import Path
import pandas as pd
import numpy as np
from .p07_baseline import ROOT,BASE,portfolios
from .reality_check import stationary_indices

OUT=BASE/'p07_optionality_001'


def market(path):
    rows=[]
    for line in path.read_text().splitlines():
        if re.match(r'^\s*\d{6},',line):
            parts=line.split(',');rows.append([parts[0].strip(),float(parts[1])/100,float(parts[4])/100])
    f=pd.DataFrame(rows,columns=['month','excess','rf']);f.index=pd.PeriodIndex(f.pop('month'),freq='M')
    if not f.index.is_unique:raise ValueError('Duplicate monthly market records')
    return f.sort_index()


def states(m):
    raw=m.excess+m.rf
    prior=(1+raw).shift(1).rolling(24,min_periods=24).apply(np.prod,raw=True)-1
    return (prior<0).astype(float).where(prior.notna())


def design(m):
    bear=states(m);r=m.excess
    return pd.DataFrame({'constant':1.,'bear':bear,'market':r,'bear_market':bear*r,
                         'bear_up_market':bear*(r>0)*r})


def register():
    OUT.mkdir(exist_ok=True)
    files=[Path(__file__),ROOT/'researchlab/p07_baseline.py',BASE/'p07_audit/m_m_pt_tot.txt',BASE/'p24_inputs/monthly_archive.txt']
    spec={'id':'P07_optionality_001','registered_utc':datetime.now(timezone.utc).isoformat(),
          'type':'Descriptive partial Table3regression3, NOT predictive entry or executable signal',
          'sample':'July1928-Mar2013; originalJan1927start truncated for strict24completepriormonthwarmup; originalauthorWML,201507vintageFrenchmonthlymarket/RF',
          'model':'WML_t=a0+aB*bear_t-1+b0*market_excess_t+bB*bear_t-1*market_excess_t+bBU*bear_t-1*I(market_excess_t>0)*market_excess_t. OLS withconstant; bear=prior24rawmarketmonthlyreturnproduct<0, allcomplete, currentmonthexcluded.',
          'targets':'PrintedTable3col3 a0=.01976,aB=.00583,b0=-.032,bB=-.661,bBU=-.815. Currentmarket/upindicator descriptiveonly, forbiddenforentry.',
          'numerical_gate':'Intercepts within.002 in decimal monthlyreturn; all3betaswithin.10. Disclose truncatedsample/vintage andall deviations; no exactreplicationclaim.',
          'inference':'5000pairedstationarymonthlyrowresamples,blocks3/12/24,seeds70303/70312/70324;95%CIforbBU. NegativebBU andallupperbounds<0 supportoptionalitymechanism only.',
          'advance':'Numericalgate andnegativeinteractionCIs permit separatepredictiveTable5audit; no strategy/ranking/paperorder.',
          'hashes':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},'sealed':'No2024-2025observations'}
    with (OUT/'registration.json').open('x') as f:json.dump(spec,f,indent=2)


def main():
    spec=json.loads((OUT/'registration.json').read_text())
    for name,digest in spec['hashes'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest
    assert not (OUT/'results.json').exists()
    m=market(BASE/'p24_inputs/monthly_archive.txt');x=design(m)
    p=portfolios(BASE/'p07_audit/m_m_pt_tot.txt',True);w=p[10]-p[1];w.index=w.index.to_period('M')
    frame=x.join(w.rename('wml')).loc['1928-07':'2013-03']
    if frame.isna().any().any():raise ValueError('Missing model rows')
    a=frame.drop(columns='wml').to_numpy();y=frame.wml.to_numpy();beta=np.linalg.lstsq(a,y,rcond=None)[0]
    intervals=[]
    for block in (3,12,24):
        rng=np.random.default_rng(70300+block);draws=[]
        for offset in range(0,5000,50):
            idx=stationary_indices(len(y),50,1/block,rng)
            draws.extend(np.linalg.lstsq(a[i],y[i],rcond=None)[0][-1] for i in idx)
        intervals.append({'block_months':block,'paths':5000,'seed':70300+block,'bBU_ci95':np.quantile(draws,[.025,.975]).tolist()})
    target=np.array([.01976,.00583,-.032,-.661,-.815]);tolerance=np.array([.002,.002,.1,.1,.1])
    numerical=bool((np.abs(beta-target)<=tolerance).all())
    result={'type':'Partial contemporaneous optionality reconstruction; not tradable forecast','n_months':len(y),
            'coefficients':dict(zip(frame.columns[:-1],beta.tolist())),'target_deviations':(beta-target).tolist(),
            'numerical_gate_pass':numerical,'bootstrap':intervals,
            'mechanism_supported':bool(numerical and beta[-1]<0 and all(r['bBU_ci95'][1]<0 for r in intervals)),
            'trading_strategy_validated':False}
    (OUT/'results.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))


if __name__=='__main__':
    import sys
    register() if '--register' in sys.argv else main()
