"""Additional literature candidates; screening is not a replication audit."""
import csv
import json
import time
import difflib
import re
from .catalog import ROOT, RESEARCH, resolve, normalize, VERIFIED_DOIS

# Canonical publisher records checked after ambiguous search matches.
VERIFIED_DOIS.update({61:'10.1016/s0304-405x(98)00027-0',88:'10.1093/rfs/hhv059'})

CANDIDATES = '''trend|Time series momentum and volatility scaling
trend|Time-series momentum versus moving average trading rules
trend|Two centuries of trend following
trend|Trends everywhere
momentum|Momentum Strategies
momentum|International Momentum Strategies
momentum|Momentum and Autocorrelation in Stock Returns
momentum|Bad News Travels Slowly: Size, Analyst Coverage, and the Profitability of Momentum Strategies
theory|A Unified Theory of Underreaction, Momentum Trading, and Overreaction in Asset Markets
theory|Investor Psychology and Security Market Under- and Overreactions
theory|A Model of Investor Sentiment
momentum|Momentum and Post-Earnings-Announcement Drift Anomalies: The Role of Liquidity Risk
momentum|Residual momentum
momentum|The Other Side of Value: The Gross Profitability Premium
reversal|Evidence of Predictable Behavior of Security Returns
reversal|Stock Return Autocorrelation and Expected Returns and Trading Costs
methodology|An Anatomy of Trading Strategies
liquidity|Commonality in liquidity
liquidity|Market Liquidity and Trading Activity
liquidity|Liquidity and Market Efficiency
liquidity|Asset pricing and the bid-ask spread
liquidity|Stock Market Liquidity and the Business Cycle
volatility|Expected Stock Returns and Volatility
volatility|On the Relation between the Expected Value and the Volatility of the Nominal Excess Return on Stocks
volatility|The Relation between Stock Returns and Their Volatility
volatility|Forecasting Stock Market Volatility: The Role of Implied Volatility, Return Asymmetry, and GARCH Modeling
allocation|Optimal Versus Naive Diversification: How Inefficient is the 1/N Portfolio Strategy?
allocation|Portfolio Selection
allocation|On the Properties of Equally-Weighted Risk Contributions Portfolios
allocation|The Properties of Equally Weighted Risk Contribution Portfolios
technical|Foundations of Technical Analysis: Computational Algorithms, Statistical Inference, and Empirical Implementation
technical|Data-Snooping, Technical Trading Rule Performance, and the Bootstrap
methodology|A Reality Check for Data Snooping
methodology|A Test for Superior Predictive Ability
methodology|The Probability of Backtest Overfitting
methodology|The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting, and Non-Normality
methodology|The Statistics of Sharpe Ratios
methodology|... and the Cross-Section of Expected Returns
methodology|Replicating Anomalies
methodology|Does Academic Research Destroy Stock Return Predictability?
methodology|The Stationary Bootstrap
etf|The mechanics of ETF arbitrage
etf|Exchange-Traded Funds, Market Structure, and the Flash Crash
etf|Do ETFs Increase the Commonality in Liquidity of Underlying Stocks?
etf|ETF Activity and Informational Efficiency of Underlying Securities
etf|The effect of ETFs on financial markets: a literature review
etf|Exchange-Traded Funds 101 for Economists
etf|ETF Sampling and Index Arbitrage
etf|The ETF premium
flows|Flow-Induced Trading Pressure and Corporate Investment
flows|Flows and Prices
flows|Asset Fire Sales (and Purchases) in Equity Markets
cross_asset|Stock Market Cross-Autocorrelations
cross_asset|Do Stock Prices Fully Reflect Information in Accruals and Cash Flows about Future Earnings?
cross_asset|Economic Links and Predictable Returns
cross_asset|Cross-Asset Return Predictability: Carry Trades, Stocks and Commodities
macro|The Other Side of the Value: Good Growth and the Gross Profitability Premium
macro|Stock Returns and Inflation
momentum|Momentum
reversal|Short-Term Reversals: The Role of Investor Sentiment
momentum|Momentum, Business Cycle, and Time-varying Expected Returns
momentum|Individualism and Momentum around the World
trend|Trend following with momentum versus moving averages: a tale of differences
momentum|The 52-week high, momentum and investor sentiment
momentum|Absolute Strength: Exploring Momentum in Stock Returns
momentum|A trend factor: Any economic gains from using information over investment horizons?
momentum|The information content of past returns
liquidity|Liquidity and Autocorrelations in Individual Stock Returns
etf|The Globalization of Financial Markets: What Do Exchange Traded Funds Tell Us?
methodology|Fact, Fiction, and Momentum Investing
methodology|Trading Costs of Asset Pricing Anomalies
methodology|The Limits of Anomalies
momentum|The Persistence of Momentum
cross_asset|Time Series Momentum and Macroeconomic Risk
technical|Technical trading revisited: False discoveries, persistence tests, and transaction costs'''

def canonical(r):
    """Prefer original published articles over identical-title CFA digests/preprints."""
    raw = json.loads((ROOT/r['source_file']).read_text(encoding='utf-8'))
    works = raw['message'].get('items', [raw['message']])
    eligible = []
    for w in works:
        title = w.get('title',[''])[0]
        score = difflib.SequenceMatcher(None,normalize(r['query_title']),normalize(title)).ratio()
        journal = ' '.join(w.get('container-title',[])).lower()
        doi = w.get('DOI','')
        if score < .90 or '/dig.' in doi or 'digest' in journal or 'erratum' in title.lower():
            continue
        eligible.append((w.get('type')=='journal-article' and 'ssrn' not in journal, score, w))
    if not eligible:
        r['match_score'] = 0
        return r
    _,score,w = max(eligible,key=lambda x:x[:2])
    r.update(match_score=score,title=' '.join(re.sub('<[^>]+>','',w['title'][0]).split()),doi=w['DOI'],
        authors=[' '.join([a.get('given',''),a.get('family','')]).strip() for a in w.get('author',[])],
        publication_date=w.get('published',{}).get('date-parts'),publication_type=w.get('type'),
        journal=w.get('container-title'),abstract=re.sub('<[^>]+>','',w.get('abstract','')),
        url=w.get('URL'),links=w.get('link',[]))
    return r

def main():
    out = RESEARCH / 'expansion_001'
    out.mkdir(exist_ok=True)
    prior = json.loads((RESEARCH/'papers.json').read_text(encoding='utf-8'))
    seen = {r['doi'].lower() for r in prior}
    names = {normalize(r['title']) for r in prior}
    accepted, screening = [], []
    for i, line in enumerate(CANDIDATES.splitlines(), 51):
        family, title = line.split('|', 1)
        try:
            r = canonical(resolve((i, (title, family))))
            reason = None
            if r['match_score'] < .90:
                reason = 'Title match requires manual resolution'
            elif i in {64,78,104,108}:
                reason = 'Valid adjacent paper, lower priority for several-day ETF signal search'
            elif r['doi'].lower() in seen or normalize(r['title']) in names:
                reason = 'Duplicate canonical work'
            elif r['publication_type'] not in ('journal-article', 'posted-content', 'report'):
                reason = 'Not a journal article or working paper'
            elif title in ('Momentum', 'The Other Side of the Value: Good Growth and the Gross Profitability Premium'):
                reason = 'Ambiguous search title excluded'
            elif any(x in r['title'].lower() for x in ['digest summary','erratum','correction']):
                reason = 'Digest or correction, not original paper'
            r['screening_status'] = reason or 'Bibliographic candidate accepted; methods not yet audited'
            screening.append(r)
            if not reason:
                seen.add(r['doi'].lower()); names.add(normalize(r['title']))
                r['candidate_id'] = f'C{len(accepted)+1:02d}'
                r['full_text_audited'] = False
                r['implementation_status'] = 'Not implemented in expansion; no performance attributed'
                r['sample_period'] = 'Not verified'
                r['reported_findings'] = 'Not asserted from metadata alone; abstract retained as source text'
                accepted.append(r)
            print(i, round(r['match_score'],3), r['doi'], r['title'], reason or 'ACCEPT', flush=True)
        except Exception as e:
            screening.append({'query_title':title,'screening_status':str(e)})
            print(i, str(e), flush=True)
        (out/'screening.json').write_text(json.dumps(screening,indent=2),encoding='utf-8')
        (out/'candidates.json').write_text(json.dumps(accepted,indent=2),encoding='utf-8')
        if len(accepted) == 50:
            break
    print('Accepted',len(accepted),flush=True)

if __name__ == '__main__':
    main()
