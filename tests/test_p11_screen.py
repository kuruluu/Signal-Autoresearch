import unittest
import numpy as np
import pandas as pd
from researchlab.p11_screen import targets,simulate,metrics


class ScreenTests(unittest.TestCase):
    def test_month_end_signal_applies_only_next_session(self):
        dates=pd.bdate_range('2020-01-01','2020-12-10')
        close=pd.Series(np.arange(len(dates))+100.,index=dates)
        signal=targets(close)
        self.assertEqual(signal.loc['2020-10-30'],0)
        self.assertEqual(signal.loc['2020-11-02'],1)
        changed=close.copy();changed.loc['2020-12-01':]=1
        pd.testing.assert_series_equal(signal.loc[:'2020-12-01'],targets(changed).loc[:'2020-12-01'])

    def test_exit_receives_overnight_gap_and_entry_does_not(self):
        dates=pd.to_datetime(['2020-01-02','2020-01-03'])
        f=pd.DataFrame({'adj_open':[100,80],'adj_close':[100,90]},index=dates)
        ret,_=simulate(f,pd.Series([1,0],index=dates),0)
        self.assertAlmostEqual(ret.iloc[1],-.2)
        ret,_=simulate(f,pd.Series([0,1],index=dates),0)
        self.assertAlmostEqual(ret.iloc[1],.125)

    def test_costs_and_initial_equity_in_drawdown(self):
        dates=pd.to_datetime(['2020-01-02']);f=pd.DataFrame({'adj_open':[100],'adj_close':[100]},index=dates)
        ret,_=simulate(f,pd.Series([1],index=dates),10)
        self.assertAlmostEqual(ret.iloc[0],1/1.001-1)
        cg,dd=metrics(np.array([-.2,.25]),1)
        self.assertAlmostEqual(cg,0);self.assertAlmostEqual(dd,.2)
