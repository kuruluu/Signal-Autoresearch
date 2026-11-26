import unittest
import numpy as np
from researchlab.p74_model import filter_model,simulate


class P74ModelTests(unittest.TestCase):
    def test_signed_shock_changes_next_variance_in_correct_direction(self):
        p=[0,0,-3,.5,0,-.3,0,0]
        positive=filter_model(p,[.02,0],[0,0],[2,3],.0025)
        negative=filter_model(p,[-.02,0],[0,0],[2,3],.0025)
        self.assertLess(positive['variance'][1],negative['variance'][1])
        self.assertAlmostEqual(np.log(negative['variance'][1]/positive['variance'][1]),.24)

    def test_seasonal_shock_is_removed_before_recursion(self):
        p=[0,0,-3,.5,0,-.3,1,0]
        seasonal=filter_model(p,[.04,0],[0,0],[10,11],.0025)
        plain=filter_model(p,[.02,0],[0,0],[9,11],.0025)
        self.assertAlmostEqual(seasonal['variance'][0]/plain['variance'][0],4)
        self.assertAlmostEqual(seasonal['fundamental_variance'][1],plain['fundamental_variance'][1])

    def test_filter_recovers_known_simulation_and_future_cannot_change_forecast(self):
        p=[.01,-4,-3,.5,25,-.2,.3,.2];months=np.arange(120)%12+1;rf=np.ones(120)*.003
        y,h,z=simulate(p,rf,months,.0025)
        f=filter_model(p,y,rf,months,.0025)
        np.testing.assert_allclose(f['fundamental_variance'],h)
        np.testing.assert_allclose(f['innovation']/np.sqrt(h),z)
        altered=y.copy();altered[60:]+=.1
        g=filter_model(p,altered,rf,months,.0025)
        np.testing.assert_allclose(f['mean'][:61],g['mean'][:61])
        np.testing.assert_allclose(f['variance'][:61],g['variance'][:61])

    def test_nonpositive_seasonal_scale_rejected(self):
        with self.assertRaises(ValueError):filter_model([0,0,-3,.5,0,-.2,-1,0],[0],[0],[10],.0025)
