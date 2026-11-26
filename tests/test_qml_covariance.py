import unittest
import numpy as np
from researchlab.qml_covariance import sandwich


class QMLTests(unittest.TestCase):
    def test_normal_mean_matches_analytic_sandwich(self):
        y=np.array([-2.,-.2,.3,1.,2.1]);variance=2.;p=np.array([y.mean()])
        def ll(theta):return -.5*(y-theta[0])**2/variance
        for step in [1e-3,1e-4]:
            r=sandwich(ll,p,step)
            self.assertAlmostEqual(r['covariance'][0,0],np.sum((y-y.mean())**2)/len(y)**2,places=6)
            self.assertAlmostEqual(r['gradient'][0],0,places=8)

    def test_flat_likelihood_rejects_unidentified_parameter(self):
        with self.assertRaises(ValueError):sandwich(lambda p:np.ones(5),[0.])
