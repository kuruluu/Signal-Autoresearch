import unittest
import numpy as np
from researchlab.p46_etf import contrast


class ContrastTests(unittest.TestCase):
    def test_single_regime_draw_is_invalid_not_zero(self):
        self.assertTrue(np.isnan(contrast(np.array([1.,2.]),np.array([True,True]))))
        self.assertAlmostEqual(contrast(np.array([2.,-.5]),np.array([False,True])),2.5)


if __name__=='__main__':unittest.main()
