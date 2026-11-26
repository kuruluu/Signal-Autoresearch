"""Explicit ETF hypotheses inspired by papers; NONE are faithful replications."""
from dataclasses import dataclass, asdict
import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Signal:
    id: str
    name: str
    papers: tuple
    family: str
    lookback: int
    available_year: int
    adaptation: str


SIGNALS = [
 Signal('S01','Own-return trend',('P01',),'trend',252,2013,'Futures to long-only ETFs; daily sampled 12-month sign, five-session cohorts; no original futures leverage.'),
 Signal('S02','Cross-ETF momentum',('P02','P13'),'momentum',126,2002,'Individual-stock long-short deciles become long-only top-three ETFs; skip last 21 sessions; no stock-level replication.'),
 Signal('S03','Sector momentum',('P12',),'sector',126,2000,'Four sector ETFs replace the full industry portfolio set; top two; shared all-ETF benchmark is supplemented by exposure diagnostics.'),
 Signal('S04','Weekly reversal',('P03','P05'),'reversal',5,1991,'Buy three lowest five-session ETF returns; no short winners, original stock weights or stock microstructure correction.'),
 Signal('S05','Long-run reversal',('P04',),'long_reversal',756,1986,'Three-year ETF loser ranking held five sessions, a severe horizon adaptation of multi-year stock reversals.'),
 Signal('S06','Near 52-week high',('P06',),'high',252,2005,'Rank ETFs by adjusted close / trailing highest adjusted close; five-session long-only holdings.'),
 Signal('S07','Risk-scaled momentum',('P08',),'risk_momentum',126,2016,'Long-only ETF momentum weighted inversely by 60-day volatility; original long-short momentum scaling not reproduced.'),
 Signal('S08','Market-state momentum',('P14',),'state_momentum',126,2005,'Cross-ETF momentum gated by positive trailing 252-session SPY return; replaces original market-state definition.'),
 Signal('S09','Unusual volume',('P15',),'volume',50,2002,'Top three ETFs by latest volume / trailing average; original event filters and month-long stock returns not reproduced.'),
 Signal('S10','Low-volume winners',('P16',),'volume_momentum',126,2001,'Momentum rank divided by relative volume; exploratory approximation, not the original turnover portfolio sorts.'),
 Signal('S11','Volume-conditioned reversal',('P17',),'volume_reversal',5,1994,'Rank negative five-day return times relative volume; simple ETF hypothesis, not structural-model replication.'),
 Signal('S12','Amihud illiquidity',('P18',),'illiquidity',60,2003,'Rank trailing absolute returns / dollar volume within a liquid ETF floor; stock liquidity premium may not transfer.'),
 Signal('S13','Stress-conditioned reversal',('P21',),'stress_reversal',5,2013,'Use past SPY realized volatility above 20% instead of VIX; this proxy does NOT test the paper\'s VIX result.'),
 Signal('S14','Inverse-variance allocation',('P24',),'inverse_variance',21,2018,'Capped per-ETF inverse realized variance allocation; no factor long-short portfolios or ex-post leverage normalization.'),
 Signal('S15','Low beta',('P27',),'low_beta',60,2015,'Long-only bottom-beta ETFs relative to SPY; no leverage or high-beta short leg, hence not BAB replication.'),
 Signal('S16','Low realized volatility',('P28','P29'),'low_volatility',60,2012,'Select low-volatility ETFs across asset classes; bonds may explain results. Not stock-decile replication.'),
 Signal('S17','Low residual volatility',('P30',),'low_idio',60,2007,'Residual variance from rolling SPY regression replaces original multi-factor idiosyncratic risk model.'),
 Signal('S18','Overnight persistence',('P41',),'overnight',5,2019,'Trailing overnight-return ranking then five-session full-day ETF holdings; does not isolate overnight execution.'),
 Signal('S19','Moving-average filter',('P11',),'ma',200,2008,'Daily 200-session average approximates monthly 10-month trend; five-session rebalancing, long-only ETFs.'),
 Signal('S20','Trading-range breakout',('P50',),'breakout',20,1993,'Adjusted ETF close above prior-window high; long-only five-session holding; original DJIA rule ensemble not replicated.'),
 Signal('S21','Multi-horizon trend',('P10',),'multi_trend',252,2018,'Average 21/63/252-session trend signs on ETFs, instead of century-long futures dataset and original portfolio construction.'),
]


def raw_weights(panel, spec, multiplier=1.0):
    c = panel['adj_close']
    returns = c.pct_change(fill_method=None)
    n = max(2, round(spec.lookback * multiplier))
    vol = returns.rolling(60).std()
    relvol = panel['volume'] / panel['volume'].rolling(50).mean()
    mom = c.shift(21) / c.shift(n + 21) - 1
    family = spec.family
    if family == 'trend':
        score = (c / c.shift(n) - 1).where(lambda x: x > 0)
    elif family in {'momentum','sector','risk_momentum','state_momentum','volume_momentum'}:
        score = mom.where(mom > 0)
        if family == 'sector':
            score.loc[:, [s for s in c.columns if s not in ['XLF','XLE','XLK','XLV']]] = np.nan
        if family == 'state_momentum':
            score.loc[c.SPY / c.SPY.shift(252) <= 1, :] = np.nan
        if family == 'volume_momentum':
            score = score / relvol
    elif family in {'reversal','long_reversal','volume_reversal','stress_reversal'}:
        score = -(c / c.shift(n) - 1)
        if family == 'volume_reversal':
            score *= relvol
        if family == 'stress_reversal':
            score.loc[vol.SPY * np.sqrt(252) <= .2, :] = np.nan
    elif family == 'high':
        score = c / c.rolling(n).max()
    elif family == 'volume':
        score = panel['volume'] / panel['volume'].rolling(n).mean()
    elif family == 'illiquidity':
        score = (returns.abs() / panel['dollar_volume']).rolling(n).mean()
    elif family == 'inverse_variance':
        variance = returns.rolling(n).var()
        return (.075 * (.15 ** 2 / 252) / variance).clip(0, .2).fillna(0)
    elif family in {'low_beta','low_idio'}:
        cov = returns.rolling(n).cov(returns.SPY)
        beta = cov.div(returns.SPY.rolling(n).var(), axis=0)
        score = -beta if family == 'low_beta' else -(returns.rolling(n).var() - beta ** 2 * returns.SPY.rolling(n).var().to_numpy()[:, None])
    elif family == 'low_volatility':
        score = -returns.rolling(n).std()
    elif family == 'overnight':
        score = np.log(panel['adj_open'] / c.shift(1)).rolling(n).sum()
    elif family == 'ma':
        score = (c / c.rolling(n).mean() - 1).where(lambda x: x > 0)
    elif family == 'breakout':
        score = (c / c.shift(1).rolling(n).max() - 1).where(lambda x: x > 0)
    elif family == 'multi_trend':
        score = sum(np.sign(c / c.shift(max(2, round(k * multiplier))) - 1) for k in (21,63,252)) / 3
        score = score.where(score > 0)
    else:
        raise ValueError(family)
    # Stable tie breaking by fixed column order, not future performance.
    ranks = score.rank(axis=1, ascending=False, method='first')
    top = 2 if family == 'sector' else 3
    weights = (ranks <= top).astype(float) * .2
    if family == 'risk_momentum':
        weights *= (vol.mean(axis=1).to_numpy()[:, None] / vol).clip(upper=2)
    return weights.fillna(0)
