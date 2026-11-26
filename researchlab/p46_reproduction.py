"""Native conditional size effect using published binary sentiment regimes."""
import argparse,io,json,re
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import pandas as pd
from .bz2007_reproduction import ROOT,BASE,digest
from .reality_check import stationary_indices

INPUT=BASE/'p46_audit';OUT=BASE/'p46_partial_001'
# Paper TableIII note supplies the binary input completely, independent of returns.
PUBLISHED_POSITIVE={1968,1969,1970,1972,*range(1979,1988),1994,1996,1997,1999,2000,2001}


def previous_year_regime(index,positive_years):
    return np.array([p.year-1 in positive_years for p in index])


def load_inputs():
    text=(INPUT/'Portfolios_Formed_on_ME.CSV').read_text()
    section=text.split('Equal Weight Returns -- Monthly',1)[1].splitlines()
    header=next(line for line in section if line.startswith(',<= 0'))
    rows=[]
    for line in section:
        if re.match(r'^\d{6},',line):rows.append(line)
        elif rows:break
    frame=pd.read_csv(io.StringIO(header+'\n'+'\n'.join(rows)),index_col=0)
    frame.columns=frame.columns.str.strip()
    frame.index=pd.PeriodIndex(frame.index.astype(str),freq='M')
    assert str(frame.index[-1])=='2020-08'
    frame=frame.loc['1963-01':'2001-12']
    assert len(frame)==468 and (frame[['Lo 10','Hi 10']]>-90).all().all()
    annual=pd.read_csv(INPUT/'annual_sentiment_1962_2001.csv').set_index('year')
    assert annual['SENT^'].notna().all()
    revised=set(annual.index[annual['SENT^']>0])
    return frame,{'published_binary':PUBLISHED_POSITIVE,'revised_author':revised}


def effect(returns,high):
    small=returns[:,0];large=returns[:,1]
    return float((large[high]-small[high]).mean()-(large[~high]-small[~high]).mean())


def register():
    files=[Path(__file__),ROOT/'researchlab/reality_check.py',INPUT/'published.pdf',INPUT/'Portfolios_Formed_on_ME.CSV',INPUT/'annual_sentiment_1962_2001.csv']
    spec={'id':'P46_partial_001','registered_at':datetime.now(timezone.utc).isoformat(),
          'target':'TableIII large-minus-small monthly spread highsentiment minus lowsentiment=1.71percentagepoints; lowbottom2.37,lowtop.92,highbottom.73,hightop.98',
          'primary_regime':'PublishedTableIII explicitly enumerated positiveannualSENTIMENTorthogonalyears; matchpreviousCALENDARyear to eachmonth, notpreviousJune',
          'sensitivity':'Revisedauthorv23annualSENT^sign fixedsecondary; cannotreplaceprimaryifbetter',
          'sample':'January1963-December2001,468monthlyobservations,39wholeyears',
          'portfolios':'Pinned2020FrenchEqualWeightReturnsMonthly Lo10andHi10,JuneformedNYSEsizebreakpoints; percentunits; nofactor/RFsubtraction',
          'approximate_gate':'primaryconditionalcontrast within.50pp/month of1.71; low-smallminuslarge>0; high-smallminuslarge<=0; primary95%CIcontrastlower>0allblocks',
          'inference':'10000stationaryresamplesofWHOLEcalendar-yearvectors, meanblocks1/3/5years,seeds46001/46003/46005; preserve12monthseasonalityandregimelabels; percentileCI. Two-labelcasesreportedbutonlypublishedbinaryprimaryclaim.',
          'deviations':['Publishedregimelabels sufficefornativebinarytestwithoutrecoveringoriginalcontinuousPCAindex; theyareexpostandnotatradablepredictor.',
                        'FrenchCRSPsizeportfoliosinstead oforiginalmergedCRSPCompustatuniverse; vintage,eligibilityanddelistingtreatmentsmaydiffer. Thisispartialreproduction,notexact.',
                        'SimpleaverageofmonthlyEWportfolioreturns; originalpooledfirmweightinginterpretationrequiresauthorcodeforexactequality.',
                        'January1963startassumedfromtablesampledescription; noendpointsearch.'],
          'files':{str(f.relative_to(ROOT)):digest(f) for f in files}}
    OUT.mkdir(exist_ok=True)
    with (OUT/'registration.json').open('x') as f:json.dump(spec,f,indent=2)


def run():
    spec=json.loads((OUT/'registration.json').read_text())
    for file,expected in spec['files'].items():assert digest(ROOT/file)==expected,file
    frame,regimes=load_inputs();returns=frame[['Lo 10','Hi 10']].to_numpy();cases={}
    for name,years in regimes.items():
        high=previous_year_regime(frame.index,years)
        cases[name]={'high_months':int(high.sum()),'low_months':int((~high).sum()),
                     'small_high':float(returns[high,0].mean()),'large_high':float(returns[high,1].mean()),
                     'small_low':float(returns[~high,0].mean()),'large_low':float(returns[~high,1].mean()),
                     'contrast_pp_month':effect(returns,high),'bootstrap':[]}
        yr=returns.reshape(39,12,2);labels=high.reshape(39,12)
        for block in (1,3,5):
            indices=stationary_indices(39,10000,1/block,np.random.default_rng(46000+block))
            values=[effect(yr[i].reshape(-1,2),labels[i].reshape(-1)) for i in indices]
            cases[name]['bootstrap'].append({'mean_block_years':block,'ci95':np.quantile(values,[.025,.975]).tolist()})
    primary=cases['published_binary']
    passed=abs(primary['contrast_pp_month']-1.71)<=.5 and primary['small_low']>primary['large_low'] and primary['small_high']<=primary['large_high'] and all(x['ci95'][0]>0 for x in primary['bootstrap'])
    result={'n':468,'cases':cases,'approximate_gate':bool(passed),'scope':'Partialnativeconditional-sizeeffect; noETFsignalclaim.'}
    with (OUT/'results.json').open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['register','run']);{'register':register,'run':run}[p.parse_args().action]()
