import unittest
import numpy as np
import pandas as pd
from researchlab.p45_timing import targets


class TimingTests(unittest.TestCase):
    def test_entry_open_excludes_pre_entry_overnight_move(self):
        p=pd.DataFrame({'open':[99.,110.,121.,130.], 'close':[100.,120.,132.,140.],
                        'adjusted_close':[100.,120.,132.,140.]})
        out=targets(p)
        self.assertAlmostEqual(out.native_close.iloc[0],.32)
        self.assertAlmostEqual(out.next_open.iloc[0],.20)
        self.assertAlmostEqual(out.second_open.iloc[0],132/121-1)
        self.assertTrue(out.iloc[-2:].isna().all().all())
        # Synthetic unit rescaling cannot change any return.
        p.adjusted_close*=.5
        np.testing.assert_allclose(targets(p),out,equal_nan=True)


if __name__=='__main__':unittest.main()
