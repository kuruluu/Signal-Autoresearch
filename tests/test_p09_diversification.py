import unittest
import numpy as np
from researchlab.p09_diversification import paired,measures


class DiversificationTests(unittest.TestCase):
    def test_explicit_source_date_typos_only(self):
        f,missing=paired([['DATE','VAL','MOM'],['20100931',.01,.02]],'2010-09','2010-09')
        self.assertEqual(len(f),1);self.assertFalse(missing)
        with self.assertRaises(ValueError):paired([['DATE','VAL','MOM'],['20110231',.01,.02]],'2011-02','2011-02')

    def test_date_boundary_missing_pair_and_duplicates(self):
        rows=[['DATE','VAL','MOM'],['20000131',.01,.02],['20000229',None,.01],['20000331',999,999]]
        frame,missing=paired(rows,'2000-01','2000-02')
        self.assertEqual(len(frame),1);self.assertEqual(missing,['2000-02'])
        with self.assertRaises(ValueError):paired(rows+[rows[1]],'2000-01','2000-02')

    def test_combo_and_vectorized_metrics_agree_with_direct_calculation(self):
        rng=np.random.default_rng(9);a=rng.normal(.005,.03,(100,2))
        s,c,r=measures(a);combo=.5*a[:,0]+.5*a[:,1]
        self.assertAlmostEqual(c,np.sqrt(12)*combo.mean()/combo.std(ddof=1))
        self.assertAlmostEqual(r,np.corrcoef(a.T)[0,1])
        bs,bc,br=measures(np.stack([a,a]))
        np.testing.assert_allclose(bs[0],s);self.assertAlmostEqual(bc[1],c)
