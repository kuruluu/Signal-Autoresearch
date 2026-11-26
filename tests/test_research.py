import unittest
import numpy as np
import pandas as pd
from researchlab.data import normalize_chart, protocol
from researchlab.engine import backtest, metrics, passive
from researchlab.signals import SIGNALS, raw_weights
from researchlab.bootstrap import inference, stationary_indices


def synthetic():
    dates = pd.bdate_range('2010-01-01', periods=1000)
    rng = np.random.default_rng(1)
    close = pd.DataFrame(100 * np.exp(np.cumsum(rng.normal(.0002, .01, (1000, 4)), axis=0)), index=dates, columns=['SPY','XLF','TLT','GLD'])
    return {'adj_close': close, 'adj_open': close * 1.001, 'close': close,
            'volume': close * 0 + 1e7, 'dollar_volume': close * 1e7}


class ResearchTests(unittest.TestCase):
    def setUp(self):
        self.panel = synthetic()
        self.p = protocol()[0]
        self.raw = self.panel['adj_close'] * 0 + .1
        self.start = self.raw.index[800]
        self.end = self.raw.index[900]

    def test_all_signals_are_causal(self):
        changed = {k: v.copy() for k, v in self.panel.items()}
        for frame in changed.values():
            frame.iloc[850:] *= 3
        for spec in SIGNALS:
            a = raw_weights(self.panel, spec)
            b = raw_weights(changed, spec)
            pd.testing.assert_frame_equal(a.iloc[:850], b.iloc[:850])

    def test_cash_costs_and_closed_lots(self):
        zero = backtest(self.panel, self.raw, self.p, self.start, self.end, cost_multiplier=0)
        costly = backtest(self.panel, self.raw, self.p, self.start, self.end, cost_multiplier=4)
        self.assertGreater(zero.daily.equity.iloc[-1], costly.daily.equity.iloc[-1])
        self.assertGreaterEqual(costly.daily.cash.min(), 0)
        self.assertEqual(costly.daily.exposure.iloc[-1], 0)
        self.assertTrue((costly.trades.sessions == 5).all())
        self.assertAlmostEqual(costly.daily.equity.iloc[-1] - self.p['capital'], costly.trades.net_pnl.sum(), places=6)

    def test_zero_price_rejected(self):
        self.panel['adj_open'].iloc[820, 0] = 0
        with self.assertRaises(ValueError):
            backtest(self.panel, self.raw, self.p, self.start, self.end)

    def test_current_close_not_available_at_open(self):
        base = self.raw * 0
        base.iloc[800, 0] = .2
        result = backtest(self.panel, base, self.p, self.start, self.end)
        self.assertEqual(result.daily.exposure.iloc[0], 0)

    def test_execution_delay(self):
        r = backtest(self.panel, self.raw, self.p, self.start, self.end, delay=1)
        self.assertEqual(r.daily.exposure.iloc[0], 0)
        self.assertGreater(r.daily.exposure.iloc[1], 0)

    def test_missed_trade_all_cash(self):
        r = backtest(self.panel, self.raw, self.p, self.start, self.end, miss=1)
        self.assertTrue((r.daily.net_return == 0).all())

    def test_bootstrap_joint_dependence_and_repeatability(self):
        x = np.random.default_rng(4).normal(0, .01, 200)
        a = inference(np.c_[x, x], count=100)
        b = inference(np.c_[x, x], count=100)
        np.testing.assert_array_equal(a['low_daily'], b['low_daily'])
        self.assertEqual(a['p_max_t'][0], a['p_max_t'][1])
        self.assertTrue((a['p_conservative'] >= a['p_one_sided']).all())

    def test_resampling_preserves_blocks(self):
        idx = stationary_indices(100, 100, 20, 5)
        consecutive = ((idx[:, 1:] - idx[:, :-1]) % 100 == 1).mean()
        self.assertGreater(consecutive, .9)

    def test_corporate_action_adjustment(self):
        chart = {'timestamp': [1577975400,1578061800], 'indicators': {
            'quote': [{'open': [100,99], 'close': [100,99], 'high': [101,100], 'low': [99,98], 'volume': [100,100]}],
            'adjclose': [{'adjclose': [99,99]}]}}
        f = normalize_chart(chart)
        self.assertEqual(f.adj_open.iloc[0], f.adj_open.iloc[1])

    def test_duplicate_dates_and_missing_prices_rejected(self):
        chart = {'timestamp':[1577975400,1577975400], 'indicators':{
            'quote':[{'open':[1,1], 'high':[1,1], 'low':[1,1], 'close':[1,1], 'volume':[1,1]}], 'adjclose':[{'adjclose':[1,1]}]}}
        with self.assertRaises(ValueError):
            normalize_chart(chart)

    def test_holdout_not_in_download_window(self):
        self.assertLessEqual(self.p['download_end_exclusive'], self.p['sealed_final'][0])


if __name__ == '__main__':
    unittest.main()
