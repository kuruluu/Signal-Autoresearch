import unittest
import numpy as np
from researchlab.p74_forecast import forecast


class P74ForecastTests(unittest.TestCase):
    def test_next_bill_proxy_and_signed_innovation_hand_calculation(self):
        p=[.01,-4,-3,.5,25,-.2,.3,.2]
        mu,v=forecast(p,[.02],[.002,.003],[9],10)
        initial_mu=.01-4*.0025
        shock=.02-initial_mu
        expected=1.3**2*np.exp(-3+.5*np.log(.0025)+25*.003-.2*shock/np.sqrt(.0025))
        self.assertAlmostEqual(v,expected)
        self.assertAlmostEqual(mu,.01-4*expected)

    def test_missing_lagged_bill_rejected(self):
        with self.assertRaises(ValueError):forecast([.01,-4,-3,.5,25,-.2,.3,.2],[.02],[.003],[9],10)
