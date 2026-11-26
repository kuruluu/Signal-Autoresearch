import unittest
import numpy as np
import pandas as pd
from researchlab.trend_followup import SPECS, weights

class FollowupTests(unittest.TestCase):
    def test_future_changes_cannot_change_any_arm(self):
        rng=np.random.default_rng(17)
        c=pd.DataFrame(np.exp(rng.normal(0,.01,(700,3)).cumsum(axis=0))*100)
        changed=c.copy();changed.iloc[500:]*=4
        for direction,sizing in SPECS.values():
            a=weights({'adj_close':c},direction,sizing)
            b=weights({'adj_close':changed},direction,sizing)
            pd.testing.assert_frame_equal(a.iloc[:500],b.iloc[:500])

    def test_negative_trends_stay_cash_without_renormalization(self):
        t=np.arange(400)
        c=pd.DataFrame({'up':100*np.exp(.001*t),'down':100*np.exp(-.001*t)})
        w=weights({'adj_close':c},'positive_return','equal')
        self.assertEqual(w.iloc[-1]['down'],0)
        self.assertAlmostEqual(w.iloc[-1]['up'],.45)
        self.assertTrue((w.iloc[:252]==0).all().all())

    def test_zero_variance_does_not_create_infinite_positions(self):
        c=pd.DataFrame(100.,index=range(400),columns=['a','b'])
        for direction,sizing in SPECS.values():
            w=weights({'adj_close':c},direction,sizing)
            self.assertTrue(np.isfinite(w.to_numpy()).all())
            if sizing=='inverse_vol': self.assertEqual(w.to_numpy().sum(),0)
