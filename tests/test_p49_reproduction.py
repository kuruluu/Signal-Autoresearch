import unittest
import numpy as np
import pandas as pd
from researchlab.p49_reproduction import regression, bootstrap


class P49Tests(unittest.TestCase):
    def test_dummy_hc1_matches_matrix_sandwich(self):
        y=np.array([1.,3.,2.,6.,7.,0.]); e=np.array([0,1,0,1,1,0],bool)
        x=np.column_stack([np.ones(6),e]); inv=np.linalg.inv(x.T@x)
        beta=inv@x.T@y; residual=y-x@beta
        cov=6/4*inv@x.T@np.diag(residual**2)@x@inv
        result=regression(y,e)
        self.assertAlmostEqual(result['coefficient'][0],beta[1])
        self.assertAlmostEqual(result['hc1_se'][0],np.sqrt(cov[1,1]))

    def test_joint_bootstrap_preserves_identical_portfolios(self):
        index=pd.bdate_range('2001-01-01','2003-12-31'); e=np.arange(len(index))%20==0
        v=np.sin(np.arange(len(index)))+e*.5
        result=bootstrap(pd.DataFrame({'a':v,'b':v},index=index),e,6,200)
        np.testing.assert_equal(result['ci95'][0],result['ci95'][1])
        self.assertEqual(result['centered_two_sided_p'][0],result['centered_two_sided_p'][1])

    def test_missing_group_fails(self):
        with self.assertRaises(ValueError): regression([1,2,3],[True,True,True])
