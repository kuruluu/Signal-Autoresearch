import unittest
import numpy as np
import pandas as pd
from researchlab.p50_reproduction import observations,estimate

class P50Tests(unittest.TestCase):
    def test_lagged_signal_on_known_path(self):
        p=pd.Series([1.,2.,1.,2.],index=pd.date_range('1900-01-01',periods=4))
        f=observations(p,2)
        np.testing.assert_allclose(f.state,[1.,-1.]);np.testing.assert_allclose(f.log_return,[-np.log(2),np.log(2)])
    def test_original_pooled_formula(self):
        f=pd.DataFrame({'log_return':[.01,.03,-.01,-.03],'state':[1,1,-1,-1]})
        r=estimate(f);self.assertAlmostEqual(r['gap'],.04)
        self.assertAlmostEqual(r['pooled_t'],.04/np.sqrt(np.var(f.log_return,ddof=1)))
    def test_future_prices_do_not_change_past_states(self):
        p=pd.Series([1.,2.,1.,2.,3.,2.]);a=observations(p,2);p.iloc[-1]=100
        b=observations(p,2);pd.testing.assert_series_equal(a.state,b.state)
    def test_ties_remain_neutral(self):
        f=observations(pd.Series([1.,1.,1.,1.]),2);self.assertTrue(f.state.eq(0).all())
