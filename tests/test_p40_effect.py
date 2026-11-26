import unittest
import numpy as np
from researchlab.p40_effect import slope,forecast


class EffectTests(unittest.TestCase):
    def test_known_linear_slope(self):
        x=np.arange(20,dtype=float)
        self.assertAlmostEqual(slope(x,3+2*x),2)

    def test_future_target_cannot_change_earlier_forecast_error(self):
        x=np.arange(10,dtype=float);y=3+2*x
        dates=np.array(['2020-01-01']*8+['2021-01-01','2021-01-02'])
        original=forecast(x,y,dates)
        self.assertAlmostEqual(original['model_mse'],0)
        # A changed final outcome affects scoring, but never its own fitted coefficients.
        changed=y.copy();changed[-1]+=10
        result=forecast(x,changed,dates)
        self.assertAlmostEqual(result['model_mse'],50)
