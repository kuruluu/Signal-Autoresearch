"""New original-vintage input, unchanged P09 diversification estimand and gates."""
import json,hashlib,datetime
from pathlib import Path
import numpy as np
from openpyxl import load_workbook
from .p09_diversification import ROOT,BASE,paired,measures
from .reality_check import stationary_indices

OUT=BASE/'p09_original_001'


def normalize(rows):
    for row in rows:
        row=list(row)
        if row and isinstance(row[0],(datetime.date,datetime.datetime)):row[0]=row[0].strftime('%Y%m%d')
        yield row


def register():
    OUT.mkdir(exist_ok=True)
    files=[Path(__file__),ROOT/'researchlab/p09_diversification.py',BASE/'p09_audit/AQR_original.xlsx']
    spec={'id':'P09_original_001','registered_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'reopen_reason':'New actual AQR explicitly original1972-2011workbook, obtained after revisedYalesource numericalmismatch. Preserve oldfailure. Nooutcomes fromnewvintagebefore registration.',
          'construction':'VME Factors DATE/VAL/MOM; normalize Excel dates to monthly labels; paired1972-Jan..2011-Jul,minimum450; same fixed50/50combo,decimalexcessreturns; author ex-postglobalweights unchanged.',
          'targets':'SRVAL.72,MOM.74,COMBO1.59,corr-.60; same.10SR/.05corr tolerances asfirsttest. Nootherweights,endpoints,thresholds.',
          'inference':'Samepaired10000pathstationaryblocks3/12/24,seeds90303/90312/90324; negativecorrupper andpositivecombo-minus-beststandaloneSRlower allblocks; numericalgatealsorequired.','limits':'Historicalaggregateeffect,notcausalexecutableaccount; no ranking/order/independentconfirmation. No reason to search additional versions if thisfails without actualsource/implementationevidence.',
          'hashes':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},'sealed':'No2024-2025observations'}
    with (OUT/'registration.json').open('x') as f:json.dump(spec,f,indent=2)


def main():
    spec=json.loads((OUT/'registration.json').read_text())
    for name,digest in spec['hashes'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest
    assert not (OUT/'results.json').exists()
    book=load_workbook(BASE/'p09_audit/AQR_original.xlsx',read_only=True,data_only=True)
    frame,missing=paired(normalize(book['VME Factors'].values));book.close()
    if len(frame)<450:raise ValueError('Insufficient pairs')
    a=frame.to_numpy();sr,combo,corr=measures(a);intervals=[]
    for block in (3,12,24):
        rng=np.random.default_rng(90300+block);rs=[];gs=[]
        for offset in range(0,10000,100):
            idx=stationary_indices(len(a),100,1/block,rng);s,c,r=measures(a[idx]);rs.extend(r);gs.extend(c-s.max(axis=-1))
        intervals.append({'block_months':block,'paths':10000,'seed':90300+block,'correlation_ci95':np.quantile(rs,[.025,.975]).tolist(),'combo_sharpe_advantage_ci95':np.quantile(gs,[.025,.975]).tolist()})
    numerical=bool((np.abs(np.r_[sr,combo]-[.72,.74,1.59])<=.1).all() and abs(corr+.6)<=.05)
    result={'type':'AQR original nativeaggregate diversification reconstruction','n_months':len(frame),'missing_months':missing,
            'sharpe_value_momentum':sr.tolist(),'sharpe_combo':float(combo),'correlation':float(corr),'numerical_gate_pass':numerical,'bootstrap':intervals,
            'advance_to_causal_execution_audit':bool(numerical and all(r['correlation_ci95'][1]<0 and r['combo_sharpe_advantage_ci95'][0]>0 for r in intervals)),
            'independent_confirmation':False,'trading_strategy_validated':False}
    (OUT/'results.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))


if __name__=='__main__':
    import sys
    register() if '--register' in sys.argv else main()
