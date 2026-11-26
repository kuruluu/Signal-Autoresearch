import unittest
import numpy as np
import pandas as pd
from researchlab.p73_causal import rolling_volatility,return_forecasts


class P73CausalTests(unittest.TestCase):
    def test_future_returns_and_volatility_do_not_change_forecast(self):
        index=pd.period_range('2000-01',periods=150,freq='M')
        v=pd.Series(.002+np.arange(150)*.00001,index=index)
        y=pd.Series(np.sin(np.arange(150))*.02,index=index)
        def mock(history):return np.sqrt(history.mean()),history.mean(),''
        original=return_forecasts(rolling_volatility(v,forecaster=mock),y)
        altered_v=v.copy();altered_y=y.copy();altered_v.iloc[125:]*=7;altered_y.iloc[125:]=-.4
        altered=return_forecasts(rolling_volatility(altered_v,forecaster=mock),altered_y)
        for col in ['forecast','mean_control','weighted_mean_control']:
            np.testing.assert_allclose(original.loc[:index[125],col],altered.loc[:index[125],col])

    def test_missing_model_is_scored_as_mean_not_dropped(self):
        index=pd.period_range('2000-01',periods=65,freq='M')
        features=pd.DataFrame({'predicted_sigma':.04,'predicted_variance':.002},index=index)
        features.loc[index[61],'predicted_sigma']=np.nan
        y=pd.Series(np.arange(65)*.0001,index=index)
        forecasts=return_forecasts(features,y)
        self.assertEqual(len(forecasts),5)
        self.assertFalse(forecasts.loc[index[61],'model_used'])
        self.assertAlmostEqual(forecasts.loc[index[61],'forecast'],y.iloc[1:61].mean())
