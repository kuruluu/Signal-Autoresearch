import unittest
import numpy as np
from researchlab.p73_reproduction import realized_variance,back_transform,weighted_regression


class P73Tests(unittest.TestCase):
    def test_adjacent_products_without_demeaning(self):
        self.assertAlmostEqual(realized_variance([.01,.02,-.01]),.0006)
        with self.assertRaises(ValueError):realized_variance([.01,-.02,.01])

    def test_lognormal_second_moment_not_squared_mean(self):
        s,v=back_transform(np.log(.05),.2)
        self.assertAlmostEqual(v/s**2,np.exp(.2))

    def test_wls_matches_direct_normal_equations(self):
        x=np.column_stack([np.ones(20),np.arange(20)]);y=np.sin(np.arange(20));s=np.arange(1,21)/10
        expected=np.linalg.solve(x.T@np.diag(1/s**2)@x,x.T@np.diag(1/s**2)@y)
        np.testing.assert_allclose(weighted_regression(y,x,s)['coefficient'],expected)
