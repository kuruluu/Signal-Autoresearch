"""Bounded, explicitly partial reconstruction of FEDS2007-11 Table 2."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'research/replication_first'
INPUT = BASE / 'bz2007_audit'
OUT = BASE / 'bz2007_partial_001'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def register():
    files = [Path(__file__), INPUT/'related_methods.html',
             INPUT/'related_variances.csv', INPUT/'spx_1989_2008.json',
             INPUT/'TB3MS_1989_2008.csv', INPUT/'bill_archive_source.json']
    spec = {
        'id': 'BZ2007_partial_001',
        'registered_at': datetime.now(timezone.utc).isoformat(),
        'target': {'slope': .86, 'intercept': -12.19, 'hac_t': 3.94,
                   'adjusted_r_squared': .1514},
        'sample': '60 nonoverlapping returns 1990Q2-2005Q1; lagged predictors 1990Q1-2004Q4',
        'response': '400*log(SPX quarterend / prior quarterend) minus prior quarterend-month TB3MS annual percentage quote',
        'estimator': 'OLS constant + lagged official IV-RV; Bartlett HAC4 without small-sample correction',
        'deviations': [
            'Paper says Jan1990-Jan2005 in text and 1990Q1-2005Q1 in tables. No1989Q4 predictor is supplied. Fixed60pair overlap; do not search endpoints.',
            'Yahoo historical S&P price series rather than documented original vendor vintage.',
            'Monthly average3month discount quote used directly as annual rate, not exact investible/log bill return. Paper does not specify conversion; this is declared approximation.',
            'TB3MS recovered from official FRED-MD December2014 vintage; not the paper original2005 vintage.',
            'Back-calculated pre2003 VIX history is retrospective; numerical reproduction does not establish live availability.'
        ],
        'approximate_match_gate': 'All: positive slope within0.20 of0.86; intercept within5 annual percentage points; adjustedR2 within0.05 of0.1514; HACt positive>=1.96. A passing gate is partial reproduction only.',
        'next_gate': 'No ETF signal or causal predictability claim from this fullsample regression; separate preregistered recursive and cost-aware test required.',
        'files': {str(f.relative_to(ROOT)): digest(f) for f in files},
    }
    OUT.mkdir(exist_ok=True)
    with (OUT/'registration.json').open('x') as f:
        json.dump(spec, f, indent=2)


def panel():
    prices = pd.DataFrame(json.loads((INPUT/'spx_1989_2008.json').read_text()))
    prices.index = pd.to_datetime(prices.pop('date')).dt.to_period('Q')
    closes = prices['close'].groupby(level=0).last()
    returns = 400*np.log(closes/closes.shift(1))
    predictors = pd.read_csv(INPUT/'related_variances.csv')
    predictors.index = pd.PeriodIndex(predictors.pop('month'), freq='M').asfreq('Q')
    predictors = predictors.groupby(level=0).last()
    bill = pd.read_csv(INPUT/'TB3MS_1989_2008.csv')
    bill.index = pd.PeriodIndex(bill.iloc[:, 0], freq='M').asfreq('Q')
    bill = pd.to_numeric(bill['TB3MS']).groupby(level=0).last()
    # Shift on a complete quarter grid, never a post-dropna row offset.
    lag = predictors.reindex(closes.index).shift(1)['iv_minus_rv']
    result = pd.DataFrame({'y': returns-bill.reindex(closes.index).shift(1), 'x': lag})
    result = result.loc['1990Q2':'2005Q1']
    assert len(result) == 60 and not result.isna().any().any()
    return result


def run():
    spec = json.loads((OUT/'registration.json').read_text())
    for file, expected in spec['files'].items():
        assert digest(ROOT/file) == expected, file
    data = panel()
    fit = sm.OLS(data.y, sm.add_constant(data.x)).fit(
        cov_type='HAC', cov_kwds={'maxlags': 4, 'use_correction': False})
    intercept, slope = fit.params
    result = {'n': len(data), 'first': str(data.index[0]), 'last': str(data.index[-1]),
              'intercept': intercept, 'slope': slope, 'hac_t': float(fit.tvalues['x']),
              'adjusted_r_squared': fit.rsquared_adj,
              'approximate_match': bool(abs(slope-.86)<=.20 and abs(intercept+12.19)<=5
                                        and abs(fit.rsquared_adj-.1514)<=.05 and fit.tvalues['x']>=1.96),
              'scope': 'Partial numerical reproduction; no out-of-sample or executable signal claim.'}
    with (OUT/'results.json').open('x') as f:
        json.dump(result, f, indent=2)
    data.to_csv(OUT/'scored_panel.csv')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['register', 'run'])
    args = parser.parse_args()
    {'register': register, 'run': run}[args.action]()
