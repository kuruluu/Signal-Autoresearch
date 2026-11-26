import unittest
import numpy as np
import pandas as pd
from researchlab.p40_sessions import extract


def session(date,opening='09:30',closing='16:00',price=100):
    index=pd.date_range(date+' '+opening,date+' '+closing,tz='America/New_York',freq='min',inclusive='left')
    return pd.DataFrame({'o':price,'c':price},index=index.tz_convert('UTC'))


class SessionTests(unittest.TestCase):
    def test_dst_and_overnight_predictor(self):
        bars=session('2023-03-13',price=102)
        rows,audit,_=extract(bars,[{'date':'2023-03-13','open':'09:30','close':'16:00'}],100)
        self.assertAlmostEqual(rows[0]['first_half_return'],.02)
        self.assertEqual(rows[0]['last_half_return'],0)
        self.assertEqual(audit[0]['status'],'eligible')
        self.assertEqual(bars.index[0].hour,13)

    def test_early_close_supplies_preceding_close_but_not_outcome(self):
        first=session('2023-11-24',closing='13:00',price=100)
        second=session('2023-11-27',price=101)
        rows,audit,_=extract(pd.concat([first,second]),[
            {'date':'2023-11-24','open':'09:30','close':'13:00'},
            {'date':'2023-11-27','open':'09:30','close':'16:00'}])
        self.assertEqual(len(rows),1)
        self.assertAlmostEqual(rows[0]['first_half_return'],.01)
        self.assertEqual(audit[0]['status'],'nonstandard_session')

    def test_missing_or_duplicate_minute_is_never_imputed(self):
        bars=session('2023-03-13')
        calendar=[{'date':'2023-03-13','open':'09:30','close':'16:00'}]
        rows,audit,_=extract(bars.drop(bars.index[12]),calendar,100)
        self.assertFalse(rows);self.assertEqual(audit[0]['status'],'missing_minutes')
        rows,audit,_=extract(pd.concat([bars,bars.iloc[:1]]),calendar,100)
        self.assertFalse(rows);self.assertEqual(audit[0]['status'],'duplicate_timestamp')

    def test_future_target_prices_do_not_change_morning_feature(self):
        bars=session('2023-03-13')
        calendar=[{'date':'2023-03-13','open':'09:30','close':'16:00'}]
        original,_,_=extract(bars,calendar,99)
        bars.loc[bars.index[-1],'c']=110
        changed,_,_=extract(bars,calendar,99)
        self.assertEqual(original[0]['first_half_return'],changed[0]['first_half_return'])
        self.assertNotEqual(original[0]['last_half_return'],changed[0]['last_half_return'])


if __name__=='__main__':unittest.main()
