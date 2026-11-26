import unittest
import pandas as pd
from researchlab.p45_strategy import simulate


class AccountingTests(unittest.TestCase):
    def test_dividend_entitlement_and_fixed_exit_with_costs(self):
        dates=pd.bdate_range('2010-01-04',periods=4)
        p=pd.DataFrame({'open':[100.,99.,100.,100.],'close':[100.,99.,100.,100.]},index=dates)
        f=pd.Series([1.,1.,1.,1.,1.],index=[pd.Timestamp('2010-01-01'),*dates])
        account,trades=simulate(p,f,{dates[0]:1.,dates[1]:1.},5)
        self.assertEqual(account.dividend_cash.iloc[0],0.)
        shares=100000/100.05
        self.assertAlmostEqual(account.dividend_cash.iloc[1],shares)
        self.assertEqual(trades[1]['date'],str(dates[1].date()))
        self.assertAlmostEqual(account.equity.iloc[1],shares*(1+99*.9995))
        self.assertEqual(len(trades),4)
        self.assertEqual(account.shares_at_close.iloc[-1],0.)

    def test_future_signal_cannot_change_earlier_account(self):
        dates=pd.bdate_range('2010-01-04',periods=8)
        p=pd.DataFrame({'open':100.,'close':101.},index=dates)
        f=pd.Series(1.,index=dates)
        first,_=simulate(p,f,{},5)
        f.iloc[5:]=-10
        changed,_=simulate(p,f,{},5)
        pd.testing.assert_frame_equal(first.iloc[:6],changed.iloc[:6])


if __name__=='__main__':unittest.main()
