import unittest
import numpy as np
import pandas as pd
from researchlab.p46_reproduction import previous_year_regime,effect


class RegimeTests(unittest.TestCase):
    def test_calendar_year_lag_does_not_switch_in_july(self):
        dates=pd.period_range('1970-01','1971-12',freq='M')
        result=previous_year_regime(dates,{1969})
        np.testing.assert_array_equal(result,np.r_[np.ones(12,dtype=bool),np.zeros(12,dtype=bool)])

    def test_contrast_direction_matches_large_minus_small(self):
        returns=np.array([[.73,.98],[2.37,.92]])
        self.assertAlmostEqual(effect(returns,np.array([True,False])),1.70)


if __name__=='__main__':unittest.main()
