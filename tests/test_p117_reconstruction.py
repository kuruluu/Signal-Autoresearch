import unittest
import pandas as pd
import numpy as np
from researchlab.p117_reconstruction import months


class CalendarTests(unittest.TestCase):
    def test_last_day_and_first_three_preserve_saturdays(self):
        dates=pd.to_datetime(['1950-01-27','1950-01-28','1950-01-30','1950-01-31',
                              '1950-02-01','1950-02-02','1950-02-03','1950-02-04','1950-02-28','1950-03-01'])
        price=pd.Series(100*1.01**np.arange(len(dates)),index=dates)
        f=months(price,'1950-01-27','1950-03-01')
        self.assertEqual(len(f),1);self.assertAlmostEqual(f.tom_sum.iloc[0],.04)
        self.assertEqual(f.rest_n.iloc[0],1)

    def test_absent_month_not_bridged_into_tom(self):
        dates=pd.to_datetime(['1914-07-30','1914-07-31','1914-12-12','1914-12-14','1914-12-15','1914-12-16','1914-12-31','1915-01-02'])
        f=months(pd.Series(np.arange(len(dates))+100,index=dates),'1914-07-30','1915-01-02')
        self.assertTrue(f.empty)
