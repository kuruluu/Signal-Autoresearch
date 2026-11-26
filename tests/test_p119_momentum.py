import unittest
import numpy as np
import pandas as pd
from researchlab.p119_momentum import weekly,expanding,slope


class WeeklyTests(unittest.TestCase):
    def test_calendar_sunday_alignment_and_no_partial_week(self):
        dates=pd.date_range('2011-01-01','2011-02-02',freq='D')
        p=pd.Series(100*1.01**np.arange(len(dates)),index=dates)
        r,f=weekly(p)
        self.assertEqual(str(r.index[0].date()),'2011-01-09')
        self.assertTrue((r.index.dayofweek==6).all())
        self.assertAlmostEqual(r.iloc[0],1.01**7-1)
        self.assertEqual((f.target_date.iloc[0]-f.index[0]).days,7)
        with self.assertRaises(ValueError):weekly(p.drop(dates[7]))

    def test_current_target_not_used_in_own_forecast(self):
        rng=np.random.default_rng(119);x=rng.normal(0,.1,150);y=.01+.2*x+rng.normal(0,.1,150)
        f=pd.DataFrame({'signal':x,'target':y});a=expanding(f)
        b=slope(x[:-1],y[:-1]);pred=y[:-1].mean()+b*(x[-1]-x[:-1].mean());error=y[-1]-pred
        f.loc[149,'target']+=1;c=expanding(f)
        self.assertAlmostEqual(c['model_mse']-a['model_mse'],(2*error+1)/46)
