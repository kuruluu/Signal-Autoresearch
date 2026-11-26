import unittest
import numpy as np
import pandas as pd
from researchlab.p52_reproduction import signals, strategy_returns, holm, bootstrap


class P52Arithmetic(unittest.TestCase):
    def test_no_same_day_return(self):
        r=pd.DataFrame({'a':[0.,.10,-.20,.30]})
        position=pd.DataFrame({'a':[True,False,True,False]})
        actual=strategy_returns(r,pd.Series([.01]*4),position)
        np.testing.assert_allclose(actual.a.iloc[1:], [.10,.01,.30])

    def test_sma_identity_and_ties(self):
        r=pd.DataFrame({'a':[0.,0.,.1,-.1,.2,0.]})
        ma,mom,p,s=signals(r,2)
        np.testing.assert_allclose((2*s.diff()).iloc[2:],(p-p.shift(2)).iloc[2:],atol=1e-14)
        flat=pd.DataFrame({'a':[0.]*5})
        ma,mom,_,_=signals(flat,2)
        self.assertFalse(ma.iloc[2:].to_numpy().any())
        self.assertFalse(mom.iloc[2:].to_numpy().any())

    def test_future_changes_do_not_change_earlier_positions(self):
        r=pd.DataFrame({'a':[.01,-.02,.03,.01,-.01,.02]})
        changed=r.copy();changed.iloc[4:]=.9
        for x,y in zip(signals(r,2)[:2],signals(changed,2)[:2]):
            pd.testing.assert_frame_equal(x.iloc[:4],y.iloc[:4])

    def test_joint_resampling_and_holm(self):
        np.testing.assert_allclose(holm([.01,.04,.03]),[.03,.06,.06])
        x=np.arange(20)/100
        out=bootstrap(np.column_stack([x,x]),3,paths=100)
        self.assertEqual(out['percentile_95_monthly_pp'][0],out['percentile_95_monthly_pp'][1])


if __name__=='__main__':unittest.main()
