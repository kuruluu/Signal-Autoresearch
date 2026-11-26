import unittest
import numpy as np
from researchlab.p82_rules import fixed_hold,positions


class P82RuleTests(unittest.TestCase):
    def test_hold_ignores_events_until_expiry(self):
        np.testing.assert_equal(fixed_hold([1,-1,0,-1,0,0],3),[1,1,1,-1,-1,-1])

    def test_future_prices_cannot_change_previous_positions(self):
        p=np.exp(np.arange(400)*.001);a=positions(p);p[300:]*=.5;b=positions(p)
        np.testing.assert_equal(a.iloc[:300].to_numpy(),b.iloc[:300].to_numpy())

    def test_band_is_neutral_on_constant_prices(self):
        p=positions(np.ones(300));self.assertTrue((p==0).all().all())
