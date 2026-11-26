import unittest
import numpy as np
import pandas as pd
from researchlab.p45_reproduction import assemble


class AlignmentTests(unittest.TestCase):
    def test_calendar_controls_and_session_outcomes_are_distinct(self):
        sessions=pd.bdate_range('2010-01-01',periods=30)
        calendar=pd.date_range(sessions[0],sessions[-1])
        prices=pd.Series(100*1.01**np.arange(30),index=sessions)
        fears=pd.Series(1.,index=sessions[6:])
        vix=pd.Series(20.,index=sessions)
        macro=pd.Series(np.arange(len(calendar),dtype=float),index=calendar)
        frame=assemble(prices,fears,vix,macro,macro)
        monday=next(d for d in frame.index if d.weekday()==0)
        self.assertEqual(frame.loc[monday,'epu_change'],1.)
        self.assertAlmostEqual(frame.loc[monday,'future2'],1.01**2-1)
        np.testing.assert_allclose(frame.return_lag5,.01)
        altered=prices.copy();altered.iloc[-1]*=2
        updated=assemble(altered,fears,vix,macro,macro)
        pd.testing.assert_frame_equal(frame.iloc[:-3],updated.iloc[:-3])


if __name__=='__main__':unittest.main()
