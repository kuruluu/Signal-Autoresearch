import unittest
import numpy as np
import pandas as pd
from researchlab.p24_bridge import rebalance,simulate,holm

class BridgeTests(unittest.TestCase):
    def test_rebalance_is_self_financing_both_directions(self):
        for old,weight in [(0,.7),(.8,.2),(.5,.5)]:
            after,risky,cash,fee=rebalance(1,old,weight,.01)
            self.assertAlmostEqual(after+fee,1)
            self.assertAlmostEqual(risky+cash,after)
            self.assertAlmostEqual(risky/after,weight)
            self.assertAlmostEqual(fee,.01*abs(risky-old))

    def test_cash_and_asset_returns_hand_calculation(self):
        i=pd.PeriodIndex(['2012-01'],freq='M')
        result=simulate(pd.Series(.5,index=i),pd.Series(.1,index=i),pd.Series(.02,index=i),0)
        self.assertAlmostEqual(result.net_return.iloc[0],.06)

    def test_flat_market_round_trip_fee(self):
        i=pd.PeriodIndex(['2012-01','2012-02'],freq='M')
        result=simulate(pd.Series(1.,index=i),pd.Series(0.,index=i),pd.Series(0.,index=i),.01)
        self.assertAlmostEqual(result.equity.iloc[-1],.99/1.01)

    def test_holm_known_example(self):
        np.testing.assert_allclose(holm([.03,.01,.04]),[.06,.03,.06])
