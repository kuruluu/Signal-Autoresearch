import unittest
import numpy as np
from researchlab.reality_check import statistics,stationary_indices


class RealityCheckTests(unittest.TestCase):
    def test_center_each_rule_before_taking_maximum(self):
        values=np.array([[1,4],[3,0],[2,2]],float);idx=np.array([[0,0,0],[1,1,1],[0,1,2]])
        observed,draws=statistics(values,idx)
        self.assertAlmostEqual(observed,2*np.sqrt(3))
        np.testing.assert_allclose(draws,np.sqrt(3)*np.array([2,1,0]))

    def test_duplicate_rule_cannot_change_family_maximum(self):
        v=np.array([[1,4],[3,0],[2,2]],float);idx=np.array([[0,0,0],[1,1,1]])
        a,b=statistics(v,idx);c,d=statistics(np.column_stack([v,v[:,0]]),idx)
        self.assertEqual(a,c);np.testing.assert_equal(b,d)

    def test_stationary_indices_valid_and_repeatable(self):
        a=stationary_indices(20,50,.1,np.random.default_rng(82));b=stationary_indices(20,50,.1,np.random.default_rng(82))
        np.testing.assert_equal(a,b);self.assertTrue(((a>=0)&(a<20)).all())
