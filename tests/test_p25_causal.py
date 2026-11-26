import unittest
import numpy as np
from researchlab.p25_causal import allocate


class AllocationTests(unittest.TestCase):
    def test_future_and_current_returns_do_not_enter_current_weights(self):
        rng=np.random.default_rng(25);x=rng.normal(.005,.04,200);v=np.exp(rng.normal(-7,1,200))
        original=allocate(x,v);changed=x.copy();changed[150:]+=.1
        new=allocate(changed,v)
        np.testing.assert_allclose(original[:31,2:],new[:31,2:])
        self.assertNotEqual(original[30,0],new[30,0])

    def test_exposure_bound_and_return_accounting(self):
        rng=np.random.default_rng(26);x=rng.normal(.02,.03,180);v=np.exp(rng.normal(-7,2,180))
        a=allocate(x,v)
        self.assertTrue((np.abs(a[:,2:4])<=5).all())
        np.testing.assert_allclose(a[:,0],a[:,2]*x[120:])
        np.testing.assert_allclose(a[:,1],a[:,3]*x[120:])
