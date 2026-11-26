"""FEARS SPY transfer and fixed entry-delay diagnostic, no trading claims."""
import argparse
import json
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import pandas as pd
from .p45_reproduction import INPUT, ROOT, BASE, load_panel, digest
from .p52_reproduction import holm
from .reality_check import stationary_indices

OUT=BASE/'p45_timing_001'


def targets(prices):
    close=prices.adjusted_close
    opening=prices.open*(prices.adjusted_close/prices.close)
    return pd.DataFrame({'native_close':close.shift(-2)/close-1,
                         'next_open':close.shift(-2)/opening.shift(-1)-1,
                         'second_open':close.shift(-2)/opening.shift(-2)-1})


def panel():
    p=pd.DataFrame(json.loads((INPUT/'SPY_2004_2011.json').read_text())['prices'])
    p.index=pd.to_datetime(p.pop('date'))
    controls=load_panel().drop(columns='future2')
    r=p.adjusted_close.pct_change(fill_method=None)
    for lag in range(6):controls[f'return_lag{lag}']=r.shift(lag).reindex(controls.index)
    outcomes=targets(p).reindex(controls.index)
    assert len(outcomes)==1889 and np.isfinite(outcomes.to_numpy()).all()
    return controls,outcomes


def register():
    files=[Path(__file__),ROOT/'researchlab/p45_reproduction.py',ROOT/'researchlab/reality_check.py',
           ROOT/'researchlab/p52_reproduction.py',INPUT/'SPY_2004_2011.json',BASE/'p45_partial_001/registration.json']
    # Freeze all original control inputs too, rather than trusting a prior result file.
    prior=json.loads((BASE/'p45_partial_001/registration.json').read_text())
    hashes={str(f.relative_to(ROOT)):digest(f) for f in files}
    hashes.update({name:expected for name,expected in prior['files'].items()})
    spec={'id':'P45_timing_001','registered_at':datetime.now(timezone.utc).isoformat(),
          'native_target':'Table3PanelBcol4 SPY FEARScoef.00378; same1889dates andcontrols, replacingindexreturnlags withSPYtotalreturnlags',
          'outcomes':['native_close:adjustedclose_t toadjustedclose_t+2',
                      'next_open:syntheticadjustedopen_t+1 toadjustedclose_t+2',
                      'second_open:syntheticadjustedopen_t+2 toadjustedclose_t+2'],
          'inference':'5000common stationarypairedrow resamples perblock5/10/20, seeds45705/45710/45720, regressionrefit; centeredone-sidedpositivecoefp; Holm2 fornext_open/second_open, nativeoutsidefamilydescriptive',
          'transfer_gate':'nativecoefficient within.0015 ofpublished.00378 andpositiveCI95everyblock',
          'timing_gate':'next_opencoef>=50%nativecoef,positiveCI95andHolm2p<=.05everyblock; second_open reported as fixedlatencysensitivity, not substituteprimary',
          'limitations':['Hypotheticalearliestnextopen assumesFEARScompleteandpublishedby9:30ET; actualpublicationdelaynotestablished.',
                         'Fullsample controlledassociation, retrospectiveindexnormalization/controlvintages; no prioronlyforecastorcurrentmarketclaim.',
                         'Adjustedopens are synthetic totalreturnunits, not exactquotedfills; gross diagnostic excludesfees/spread andpositionrules.',
                         'Sameviewed2004-2011developmentperiod; no independentvalidation.'],
          'files':hashes}
    OUT.mkdir(exist_ok=True)
    with (OUT/'registration.json').open('x') as f:json.dump(spec,f,indent=2)


def run():
    spec=json.loads((OUT/'registration.json').read_text())
    for name,expected in spec['files'].items():assert digest(ROOT/name)==expected,name
    controls,y=panel();scale=controls.std(ddof=0).to_numpy()
    x=np.column_stack([np.ones(len(controls)),controls.to_numpy()/scale]);pos=1+list(controls).index('fears')
    coef=np.linalg.lstsq(x,y.to_numpy(),rcond=None)[0][pos]/scale[pos-1]
    cases={name:{'coefficient':float(coef[j]),'bootstrap':[]} for j,name in enumerate(y)}
    for block in (5,10,20):
        idx=stationary_indices(len(y),5000,1/block,np.random.default_rng(45700+block))
        draws=np.array([np.linalg.lstsq(x[i],y.to_numpy()[i],rcond=None)[0][pos]/scale[pos-1] for i in idx])
        ps=(1+np.count_nonzero(draws-coef>=coef,axis=0))/5001
        adjusted=holm(ps[1:].tolist())
        for j,name in enumerate(y):
            cases[name]['bootstrap'].append({'block':block,'ci95':np.quantile(draws[:,j],[.025,.975]).tolist(),
                                             'se':float(draws[:,j].std(ddof=1)),'p':float(ps[j]),
                                             'holm2_p':None if j==0 else float(adjusted[j-1])})
        print('Completed timing block',block,flush=True)
    native=cases['native_close'];primary=cases['next_open']
    result={'n':len(y),'cases':cases,'next_open_retention':float(coef[1]/coef[0]),
            'transfer_gate':bool(abs(coef[0]-.00378)<=.0015 and all(b['ci95'][0]>0 for b in native['bootstrap'])),
            'timing_gate':bool(coef[1]>=.5*coef[0] and all(b['ci95'][0]>0 and b['holm2_p']<=.05 for b in primary['bootstrap'])),
            'scope':'Gross fullsample timing diagnostic; not validated trading signal.'}
    with (OUT/'results.json').open('x') as f:json.dump(result,f,indent=2)
    controls.join(y).to_csv(OUT/'scored_panel.csv')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['register','run'])
    {'register':register,'run':run}[p.parse_args().action]()
