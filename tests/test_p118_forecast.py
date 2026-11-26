import unittest
import numpy as np
import pandas as pd
from researchlab.p118_forecast import panel,expanding,slope


class ForecastTests(unittest.TestCase):
    def test_next_quarter_signal_cannot_use_current_quarter_prices(self):
        dates=pd.bdate_range('1993-01-29','1995-12-29');rng=np.random.default_rng(118)
        close=100*np.exp(np.cumsum(rng.normal(0,.01,len(dates))))
        p=pd.DataFrame({'open':close/1.001,'close':close,'adj_close':close},index=dates)
        rf=pd.Series(0.,index=dates);a=panel(p,rf)
        q=p.copy();q.loc['1994-04-01':,'open']*=1.1;b=panel(q,rf)
        self.assertAlmostEqual(a.loc['1994Q2','signal'],b.loc['1994Q2','signal'])
        self.assertNotEqual(a.loc['1994Q3','signal'],b.loc['1994Q3','signal'])

    def test_overnight_identity_and_quarter_compounding(self):
        dates=pd.bdate_range('1993-01-29','1994-12-30')
        close=100*1.001**np.arange(len(dates))
        p=pd.DataFrame({'open':close,'close':close,'adj_close':close},index=dates)
        f=panel(p,pd.Series(0.,index=dates));n=int((dates.to_period('Q')=='1993Q3').sum())
        self.assertAlmostEqual(f.loc['1993Q3','target'],1.001**n-1)

    def test_current_target_excluded_from_own_forecast(self):
        x=np.arange(50,dtype=float);y=.01*x+np.sin(x)*.001
        f=pd.DataFrame({'signal':x,'target':y});a=expanding(f)
        b=slope(x[:-1],y[:-1]);prediction=y[:-1].mean()+b*(x[-1]-x[:-1].mean());error=y[-1]-prediction
        f.loc[49,'target']+=1;c=expanding(f)
        self.assertAlmostEqual(c['model_mse']-a['model_mse'],(2*error+1)/10)
