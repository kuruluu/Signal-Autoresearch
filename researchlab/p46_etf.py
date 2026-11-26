"""Fixed ETF transfer of the conditional size effect, not a trading rule."""
import argparse,json
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import pandas as pd
from .bz2007_reproduction import ROOT,BASE,digest
from .reality_check import stationary_indices

INPUT=BASE/'p46_audit';OUT=BASE/'p46_etf_001'


def contrast(spread,high):
    if not high.any() or high.all():return np.nan
    return float(spread[~high].mean()-spread[high].mean())


def load_panel():
    values={}
    for symbol in ('IWM','SPY'):
        data=pd.DataFrame(json.loads((INPUT/f'{symbol}_2000_2011.json').read_text()))
        data.index=pd.to_datetime(data.pop('date')).dt.to_period('M')
        values[symbol]=data.adjusted_close.groupby(level=0).last().pct_change(fill_method=None)*100
    frame=pd.DataFrame(values).loc['2001-01':'2011-12']
    # This earlier extract ends2001; use the original archived workbook for2000-2010.
    annual=pd.read_excel(INPUT/'sentiment_v23_archived.xlsx',sheet_name='POST Annual',header=21,na_values='.')
    annual.columns=annual.columns.astype(str).str.strip();annual=annual.set_index('year')
    score=np.array([annual.loc[p.year-1,'SENT^'] for p in frame.index],float)
    assert len(frame)==132 and np.isfinite(frame.to_numpy()).all() and np.isfinite(score).all()
    frame['sentiment']=score;frame['high']=score>0;frame['small_minus_large']=frame.IWM-frame.SPY
    return frame


def register():
    files=[Path(__file__),ROOT/'researchlab/reality_check.py',INPUT/'sentiment_v23_archived.xlsx',
           INPUT/'IWM_2000_2011.json',INPUT/'SPY_2000_2011.json']
    spec={'id':'P46_etf_001','registered_at':datetime.now(timezone.utc).isoformat(),
          'estimand':'MeanIWMminusSPYmonthlytotalreturnlowsentiment minusmeanIWMminusSPYhighsentiment; sameconditionalspreadorientationasnativeeffect',
          'sample':'Jan2001-Dec2011,132months,11wholecalendaryears; previouscalendar-year annualSENT^fromarchivedv23, nootherthresholdorwindow',
          'transfer_gate':'Contrast>=.25percentagepoints/month andCI95lower>0andcenteredone-sidedp<=.05forALLblocks1/2/3years; >=95%bootstrapdrawsnondegenerateeachblock',
          'inference':'10000wholecalendar-yearstationarybootstrapresamples eachblock1/2/3,seed46101/46102/46103; resamplemonthlyspreadandregimetogether; reportinvalidsingle-regimedrawsandconditionalonvaliddrawCI',
          'limits':['ETFcapweightedRussell2000/SP500differsmateriallyfromEWNYSEbottom/topsize-deciles; noexactreplicationclaim.',
                   'Short11yearhistoryandfewregimechanges; conditionalvalidbootstrapcanbesensitive; gatefailureisinconclusiveifprecisionpoor.',
                   'RevisedretrospectivePCAseriesandpublicationtimeunresolved, nohistoricalcausalavailabilityclaim.',
                   'Adjustedclosemonthlytotalreturns, grossassociationnotcostawareexecution. Alreadyvieweddevelopmentnotindependentholdout.'],
          'files':{str(f.relative_to(ROOT)):digest(f) for f in files}}
    OUT.mkdir(exist_ok=True)
    with (OUT/'registration.json').open('x') as f:json.dump(spec,f,indent=2)


def run():
    spec=json.loads((OUT/'registration.json').read_text())
    for file,expected in spec['files'].items():assert digest(ROOT/file)==expected,file
    frame=load_panel();spread=frame.small_minus_large.to_numpy();high=frame.high.to_numpy()
    observed=contrast(spread,high);yearspread=spread.reshape(11,12);yearhigh=high.reshape(11,12);boot=[]
    for block in (1,2,3):
        indices=stationary_indices(11,10000,1/block,np.random.default_rng(46100+block))
        draws=np.array([contrast(yearspread[i].reshape(-1),yearhigh[i].reshape(-1)) for i in indices])
        valid=np.isfinite(draws);good=draws[valid]
        p=(1+np.count_nonzero(good-observed>=observed))/(len(good)+1)
        boot.append({'block_years':block,'valid_fraction':float(valid.mean()),'invalid_draws':int((~valid).sum()),
                     'ci95':np.quantile(good,[.025,.975]).tolist(),'p':float(p),'p_mc_se':float(np.sqrt(p*(1-p)/len(good)))})
    result={'n':132,'high_months':int(high.sum()),'low_months':int((~high).sum()),
            'small_minus_large_low':float(spread[~high].mean()),'small_minus_large_high':float(spread[high].mean()),
            'contrast_pp_month':observed,'bootstrap':boot,
            'passes_gate':bool(observed>=.25 and all(b['valid_fraction']>=.95 and b['ci95'][0]>0 and b['p']<=.05 for b in boot)),
            'scope':'ETFconditionalassociationdevelopmenttest, not trading signal.'}
    with (OUT/'results.json').open('x') as f:json.dump(result,f,indent=2)
    frame.to_csv(OUT/'scored_panel.csv');print(json.dumps(result,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['register','run']);{'register':register,'run':run}[p.parse_args().action]()
