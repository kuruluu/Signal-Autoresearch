import unittest
import numpy as np
import pandas as pd
from researchlab.p24_reproduction import ols,construct

class P24Tests(unittest.TestCase):
    def fixture(self):
        dates=pd.to_datetime(['1926-07-01','1926-07-02','1926-07-03','1926-08-01','1926-08-02','1926-09-01','1926-09-02'])
        d=pd.DataFrame({'vwretd':[.01,.02,.03,0,.04,.01,.02],'rf':0},index=dates)
        m=pd.DataFrame({'market':[.05,.03]},index=pd.PeriodIndex(['1926-08','1926-09'],freq='M'))
        return d,m

    def test_known_regression_coefficients(self):
        x=np.array([-1.,0,1,2]);e=np.array([-1.,1,1,-1])
        r=ols(.5+.2*x+e,x)
        self.assertAlmostEqual(r['alpha_annual_pct'],600)
        self.assertAlmostEqual(r['beta'],.2)
        self.assertEqual(r['n'],4)

    def test_variance_uses_previous_month(self):
        d,m=self.fixture();f,c=construct(d,m)
        self.assertAlmostEqual(f.lagged_realized_variance.iloc[0],2*.01**2/3)
        self.assertAlmostEqual(f.lagged_realized_variance.iloc[1],.02**2)
        self.assertAlmostEqual(f.managed.std(),f.factor.std())

    def test_hc1_finite_sample_factor(self):
        x=np.arange(20.);y=.1+.2*x+np.sin(x)
        a=ols(y,x,hc1=False);b=ols(y,x,hc1=True)
        self.assertAlmostEqual(b['alpha_se_annual_pct']/a['alpha_se_annual_pct'],np.sqrt(20/18))

    def test_sealed_data_rejected(self):
        d,m=self.fixture();d.loc[pd.Timestamp('2024-01-02')]=[.01,0]
        with self.assertRaises(ValueError):construct(d,m)
