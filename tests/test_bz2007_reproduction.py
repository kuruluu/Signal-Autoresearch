import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
from researchlab import bz2007_reproduction as study


class QuarterAlignmentTests(unittest.TestCase):
    def test_predictors_and_bill_are_lagged_one_calendar_quarter(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            months = pd.period_range('1989-12', '2005-03', freq='M')
            prices = [{'date': str(m.end_time.date()), 'close': float(np.exp(i*.01))}
                      for i, m in enumerate(months)]
            (root/'spx_1989_2008.json').write_text(json.dumps(prices))
            pd.DataFrame({'month': months.astype(str), 'iv_minus_rv': np.arange(len(months))}).to_csv(
                root/'related_variances.csv', index=False)
            pd.DataFrame({'date': months.astype(str), 'TB3MS': np.arange(len(months))*.1}).to_csv(
                root/'TB3MS_1989_2008.csv', index=False)
            with patch.object(study, 'INPUT', root):
                panel = study.panel()
                self.assertEqual(len(panel), 60)
                self.assertEqual(panel.iloc[0].x, 3)  # March1990 predictor, June1990 outcome
                self.assertAlmostEqual(panel.iloc[0].y, 12-.3)
                # Alter a future quarter's inputs: earlier pairs must remain identical.
                predictors = pd.read_csv(root/'related_variances.csv')
                predictors.loc[predictors.month >= '2000-01', 'iv_minus_rv'] = -999
                predictors.to_csv(root/'related_variances.csv', index=False)
                changed = study.panel()
                pd.testing.assert_frame_equal(panel.loc[:'1999Q4'], changed.loc[:'1999Q4'])


if __name__ == '__main__':
    unittest.main()
