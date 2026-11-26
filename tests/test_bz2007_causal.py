import unittest
import numpy as np
import pandas as pd
from researchlab.bz2007_causal import forecasts, inference


class PriorOnlyTests(unittest.TestCase):
    def test_current_and_future_outcomes_do_not_change_current_prediction(self):
        index=pd.period_range('1990Q2',periods=75,freq='Q')
        x=np.sin(np.arange(75))
        data=pd.DataFrame({'x':x,'y':2+3*x},index=index)
        original=forecasts(data)
        changed=data.copy();changed.loc['2002Q1':,'y']=99999
        altered=forecasts(changed)
        np.testing.assert_allclose(original.loc[original.quarter<='2002Q1','forecast'],
                                   altered.loc[altered.quarter<='2002Q1','forecast'])
        np.testing.assert_allclose(original.forecast,original.actual,atol=1e-12)
        self.assertTrue((original.training_last<original.quarter).all())

    def test_constant_predictor_falls_back_to_mean_and_marks_invalid(self):
        data=pd.DataFrame({'x':np.ones(75),'y':np.arange(75)},
                          index=pd.period_range('1990Q2',periods=75,freq='Q'))
        output=forecasts(data)
        self.assertFalse(output.valid.any())
        np.testing.assert_array_equal(output.forecast,output.historical_mean)

    def test_zero_loss_gain_cannot_pass_inference(self):
        for row in inference(np.zeros(36),paths=100):
            self.assertEqual(row['one_sided_centered_p'],1)
            self.assertEqual(row['ci95'],[0,0])


if __name__=='__main__': unittest.main()
