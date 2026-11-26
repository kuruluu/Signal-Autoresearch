import unittest
import pandas as pd
from researchlab.p52_bridge import execution_inputs, close_positions

class P52BridgeTests(unittest.TestCase):
    def test_open_return_does_not_include_prior_overnight(self):
        dates=pd.bdate_range('2010-01-01',periods=55)
        f=pd.DataFrame({'adj_close':range(100,155),'adj_open':[100.]*55},index=dates)
        f.loc[dates[52],'adj_open']=200
        w,r,c=execution_inputs(f,pd.Series(.001,index=dates),str(dates[51].date()),str(dates[52].date()))
        self.assertTrue(w.MA.eq(1).all())
        self.assertEqual(r.iloc[0],1.)
        self.assertEqual(r.iloc[1],-.5)
    def test_future_gap_cannot_change_current_weight(self):
        dates=pd.bdate_range('2010-01-01',periods=55)
        prices=pd.Series(range(100,155),index=dates,dtype=float)
        a=close_positions(prices).shift(1)
        prices.iloc[-1]=1
        b=close_positions(prices).shift(1)
        pd.testing.assert_frame_equal(a,b)
