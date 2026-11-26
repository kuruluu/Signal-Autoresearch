"""Fixed FEARS-positive SPY/cash development test; hypothetical availability."""
import argparse,json
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import pandas as pd
from .p45_reproduction import ROOT,BASE,INPUT,digest
from .reality_check import stationary_indices

OUT=BASE/'p45_strategy_001'


def simulate(prices,fears,dividends,cost_bps=5):
    cash=100000.;shares=0.;exit_index=-1;previous_equity=cash
    c=cost_bps/10000;rows=[];trades=[]
    for i,(date,bar) in enumerate(prices.iterrows()):
        # Entitlement belongs to holders from the previous close, before ex-date buys.
        distribution=shares*float(dividends.get(date,0.));cash+=distribution
        earlier=fears.loc[fears.index<date] if i==0 else None
        prior=fears.get(prices.index[i-1],np.nan) if i else (earlier.iloc[-1] if len(earlier) else np.nan)
        if shares==0 and prior>0 and i<len(prices)-1:
            fill=bar.open*(1+c);shares=cash/fill;cash=0.;exit_index=i+1
            trades.append({'date':str(date.date()),'side':'buy','fill':fill,'shares':shares})
        if shares>0 and (i==exit_index or i==len(prices)-1):
            fill=bar.close*(1-c);cash+=shares*fill
            trades.append({'date':str(date.date()),'side':'sell','fill':fill,'shares':shares});shares=0.
        equity=cash+shares*bar.close
        assert cash>=-1e-8 and equity>0
        rows.append({'date':str(date.date()),'equity':equity,'return':equity/previous_equity-1,
                     'cash':cash,'shares_at_close':shares,'dividend_cash':distribution})
        previous_equity=equity
    return pd.DataFrame(rows),trades


def inputs():
    source=json.loads((INPUT/'SPY_2004_2011.json').read_text());p=pd.DataFrame(source['prices'])
    p.index=pd.to_datetime(p.pop('date'));assert np.isfinite(p[['open','close']]).all().all()
    assert not source['events'].get('splits',{})  # Reject, never silently mishandle splits.
    dividends={pd.Timestamp(datetime.fromtimestamp(v['date'],timezone.utc).date()):v['amount']
               for v in source['events'].get('dividends',{}).values()}
    f=pd.read_csv(INPUT/'fears_post_20140512.csv');f=pd.Series(f.fears30.to_numpy(),index=pd.to_datetime(f.date))
    return p,f,dividends


def register():
    files=[Path(__file__),ROOT/'researchlab/reality_check.py',INPUT/'SPY_2004_2011.json',INPUT/'fears_post_20140512.csv']
    spec={'id':'P45_strategy_001','registered_at':datetime.now(timezone.utc).isoformat(),
          'sample':'2007-07-02 through2011-12-30, previouslyvieweddevelopment; initial100000cash, no fittedparameters',
          'rule':'Whenflat atopen, previousmarket-sessionFEARS30>0 buysSPYallcash; exitatcloseofsecondholdingsession; ignoreinterveningsignals, noleverage/shorts; noentryifinsufficientexitbars',
          'accounting':'Rawopens/closes,fractionalshares,adversefillcostperside0/5/10bps; dividendexdateentitlementfrompreviousclose, creditedcashsameexdate (paydatelagapproximation); cashyieldzero; rejectsplits;terminalflat',
          'controls':'cash and fixed50%SPY/50%cash constantmix, usingrawclose-to-close totalreturns incldistributions; controlignoresrebalancingfees, makingcomparisonharder; fullSPYbuyholdreporteddiagnostic',
          'primary':'At5bpsperside:annualizedmean dailyreturnadvantage over50%control>=2percentagepoints andpositiveCI95allblocks5/10/20 andone-sidedcenteredp<=.05; netmeanabovezero; strategyvol<=1.25controlvol. Also10bpscase mustmeanoutperformcontrol,notseparateprimaryclaim.',
          'inference':'10000pairedstationarydailyreturnpaths perblock5/10/20, seeds45905/45910/45920; conditionalfixedstrategyreturns,no fullhistoryresimulation; annualmeans252,notCAGR. ReportpMonteCarlostandarderror; ifpwithin2SEof.05,100000same-seedpathsforblock.',
          'limitations':['HypotheticalFEARSavailabilitybynextopen; actualpostingtimeandretrospectivenormalizationunverified.',
                         'Rawvendorhistoricalopens are reportedauctionprices, noorderbook/liquidityreconstruction; coststressassumptionnotexactfills.',
                         'No livebrokerorders,no2024-2025data,no independentconfirmation; desiredobjectiveeconomicincrementalreturn,notjustvolatilityreduction.'],
          'files':{str(f.relative_to(ROOT)):digest(f) for f in files}}
    OUT.mkdir(exist_ok=True)
    with (OUT/'registration.json').open('x') as f:json.dump(spec,f,indent=2)


def loss_bootstrap(active,block,paths):
    indices=stationary_indices(len(active),paths,1/block,np.random.default_rng(45900+block))
    observed=active.mean();draws=active[indices].mean(axis=1)
    p=float((1+np.count_nonzero(draws-observed>=observed))/(paths+1))
    return {'block':block,'paths':paths,'annual_ci95':(252*np.quantile(draws,[.025,.975])).tolist(),
            'p':p,'p_mc_se':float(np.sqrt(p*(1-p)/paths))}


def run():
    spec=json.loads((OUT/'registration.json').read_text())
    for file,expected in spec['files'].items():assert digest(ROOT/file)==expected,file
    prices,fears,dividends=inputs();total=(prices.close+pd.Series(dividends).reindex(prices.index,fill_value=0))/prices.close.shift(1)-1
    prices=prices.loc['2007-07-02':'2011-12-30'];total=total.reindex(prices.index)
    outcomes={};frames={}
    for cost in (0,5,10):
        frame,trades=simulate(prices,fears,dividends,cost);frames[cost]=frame
        (OUT/f'trades_{cost}bps.json').write_text(json.dumps(trades,indent=2))
        frame.to_csv(OUT/f'account_{cost}bps.csv',index=False)
        outcomes[str(cost)]={'trades':len(trades)//2,'annual_mean':float(252*frame['return'].mean()),
                             'terminal_equity':float(frame.equity.iloc[-1]),
                             'annual_vol':float(np.sqrt(252)*frame['return'].std(ddof=1))}
    control=.5*total.to_numpy();active=frames[5]['return'].to_numpy()-control
    boot=[]
    for block in (5,10,20):
        result=loss_bootstrap(active,block,10000)
        if abs(result['p']-.05)<=2*result['p_mc_se']:result=loss_bootstrap(active,block,100000)
        boot.append(result)
    advantage=float(252*active.mean());control_mean=float(252*control.mean());control_vol=float(np.sqrt(252)*control.std(ddof=1))
    passed=advantage>=.02 and outcomes['5']['annual_mean']>0 and outcomes['5']['annual_vol']<=1.25*control_vol and outcomes['10']['annual_mean']>control_mean and all(x['annual_ci95'][0]>0 and x['p']<=.05 for x in boot)
    result={'n':len(prices),'cases':outcomes,'control_annual_mean':control_mean,'control_annual_vol':control_vol,
            'buyhold_annual_mean':float(252*total.mean()),'annual_active_mean_5bps':advantage,
            'bootstrap':boot,'passes_gate':bool(passed),'scope':'Conditionaldevelopmentstrategy; FEARSreal-timeavailabilityunproven.'}
    with (OUT/'results.json').open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['register','run']);{'register':register,'run':run}[p.parse_args().action]()
