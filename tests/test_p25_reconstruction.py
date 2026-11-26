import unittest
import pandas as pd
import numpy as np
from researchlab.p25_reconstruction import assemble


class VarianceTests(unittest.TestCase):
    def test_prior_calendar_month_second_moment_not_demeaned(self):
        daily=pd.Series([.01,.01,.02,.02],index=pd.to_datetime(['2000-12-28','2000-12-29','2001-01-02','2001-01-03']))
        monthly=pd.Series([.03,-.01],index=pd.period_range('2001-01',periods=2,freq='M'))
        frame,scale=assemble(daily,monthly,'2001-01','2001-02')
        self.assertAlmostEqual(frame.lag_variance.iloc[0],22*.01**2)
        self.assertAlmostEqual(frame.lag_variance.iloc[1],22*.02**2)
        self.assertAlmostEqual(frame.original.std(),frame.managed.std())

    def test_absent_prior_month_rejected(self):
        daily=pd.Series([.01],index=pd.to_datetime(['2001-01-02']))
        monthly=pd.Series([.03,-.01],index=pd.period_range('2001-01',periods=2,freq='M'))
        with self.assertRaises(ValueError):assemble(daily,monthly,'2001-01','2001-02')
