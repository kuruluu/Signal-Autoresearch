import unittest
import pandas as pd
import numpy as np
from researchlab.p07_optionality import states


class StateTests(unittest.TestCase):
    def test_24_prior_months_required_current_excluded(self):
        idx=pd.period_range('2000-01',periods=27,freq='M')
        m=pd.DataFrame({'excess':-.01,'rf':0.},index=idx)
        a=states(m);self.assertTrue(a.iloc[:24].isna().all());self.assertEqual(a.iloc[24],1)
        m.iloc[24,0]=100
        b=states(m);self.assertEqual(b.iloc[24],1);self.assertEqual(b.iloc[25],0)
