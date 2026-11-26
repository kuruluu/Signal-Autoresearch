import unittest
import numpy as np
import pandas as pd
from researchlab.p17_effect import assemble,expanding,design


def prices():
    idx=pd.bdate_range('2014-01-01',periods=800)
    rng=np.random.default_rng(17)
    return pd.DataFrame({'adj_close':100*np.exp(np.cumsum(rng.normal(0,.01,len(idx)))),
                         'adj_open':100*np.exp(np.cumsum(rng.normal(0,.01,len(idx)))),
                         'volume':np.exp(rng.normal(15,.3,len(idx)))},index=idx)


class AlignmentTests(unittest.TestCase):
    def test_volume_normalization_excludes_current(self):
        p=prices();i=300;f=assemble(p)
        expected=np.log(p.volume.iloc[i])-np.log(p.volume.iloc[i-252:i]).mean()
        self.assertAlmostEqual(f.loc[p.index[i],'volume'],expected)
        self.assertEqual(f.loc[p.index[i],'target_date'],p.index[i+1])
        self.assertAlmostEqual(f.loc[p.index[i],'target'],p.adj_close.iloc[i+1]/p.adj_open.iloc[i+1]-1)

    def test_future_data_do_not_change_prior_features(self):
        p=prices();a=assemble(p);q=p.copy();q.iloc[500:,q.columns.get_loc('volume')]*=3
        b=assemble(q)
        pd.testing.assert_frame_equal(a.loc[:p.index[499]],b.loc[:p.index[499]])

    def test_current_target_is_not_in_own_fit(self):
        f=assemble(prices());a=expanding(f)
        g=f.copy();g.iloc[-1,g.columns.get_loc('target')]+=1
        b=expanding(g)
        x=design(f);y=f.target.to_numpy()
        prediction=x[-1]@np.linalg.lstsq(x[:-1],y[:-1],rcond=None)[0]
        error=y[-1]-prediction
        self.assertAlmostEqual(b['candidate_mse']-a['candidate_mse'],(2*error+1)/a['n'])
        # Earlier history unchanged: only the final scoring error may change.
        pd.testing.assert_frame_equal(f.iloc[:-1],g.iloc[:-1])
