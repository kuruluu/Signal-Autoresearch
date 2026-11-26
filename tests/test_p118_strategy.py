import unittest
import numpy as np
import pandas as pd
from researchlab.p118_strategy import simulate,allocations


class LedgerTests(unittest.TestCase):
    def test_second_session_fill_whole_shares_and_cash_budget(self):
        idx=pd.bdate_range('2000-01-03',periods=4)
        p=pd.DataFrame({'open':100.,'close':100.},index=idx)
        f,trades=simulate(p,pd.Series([1.],index=pd.PeriodIndex(['2000Q1'],freq='Q')),{},bps=5)
        self.assertEqual(f.shares.iloc[0],0);self.assertEqual(trades[0]['date'],'2000-01-04')
        self.assertEqual(trades[0]['quantity'],99);self.assertTrue((f.cash>=0).all())

    def test_exdate_receivable_is_nav_but_not_spendable_cash(self):
        idx=pd.bdate_range('2000-01-03',periods=4)
        p=pd.DataFrame({'open':[100,100,99,99],'close':[100,100,99,99]},index=idx)
        f,_=simulate(p,pd.Series([1.],index=pd.PeriodIndex(['2000Q1'],freq='Q')),{idx[2]:1},lag=1,bps=0,commission=0)
        self.assertAlmostEqual(f.equity.iloc[2],10000);self.assertEqual(f.cash.iloc[2],0)
        self.assertEqual(f.receivable.iloc[2],100);self.assertEqual(f.cash.iloc[3],100)
        self.assertEqual(f.receivable.iloc[3],0)

    def test_current_target_cannot_change_own_allocation(self):
        rng=np.random.default_rng(118);idx=pd.period_range('1993Q3',periods=106,freq='Q')
        f=pd.DataFrame({'signal':rng.normal(0,.001,106),'target':rng.normal(.02,.05,106)},index=idx)
        signal=f.signal.copy();a,c=allocations(f,signal)
        changed=f.copy();changed.loc['2004Q1','target']+=.5;b,d=allocations(changed,signal)
        self.assertEqual(a.loc['2004Q1'],b.loc['2004Q1']);self.assertEqual(c.loc['2004Q1'],d.loc['2004Q1'])
