"""Resolve a curated bibliography against Crossref; preserve source responses."""
import concurrent.futures
import difflib
import hashlib
import json
import re
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / 'research'
VERIFIED_DOIS = {
 1:'10.1016/j.jfineco.2011.11.003',7:'10.1016/j.jfineco.2015.12.002',9:'10.1111/jofi.12021',
 10:'10.3905/jpm.2017.44.1.015',18:'10.1016/s1386-4181(01)00024-6',19:'10.1086/374184',
 20:'10.2469/faj.v69.n3.4',21:'10.1093/rfs/hhs066',24:'10.1111/jofi.12513',26:'10.1093/rfs/hhy041',
 27:'10.1016/j.jfineco.2013.10.005',28:'10.3905/jpm.2007.698039',30:'10.1111/j.1540-6261.2006.00836.x',
 31:'10.1111/jofi.12727',34:'10.1016/j.jfineco.2021.04.023',37:'10.17016/feds.2020.097',
 38:'10.1111/fima.12396',41:'10.1017/s0022109017000989',46:'10.1111/j.1540-6261.2006.00885.x',
 49:'10.1111/jofi.12196',36:'10.1093/rof/rfaa027',44:'10.1111/j.1540-6261.2011.01679.x'}

CANDIDATES = [
 ('Time series momentum', 'trend'),
 ('Returns to Buying Winners and Selling Losers: Implications for Stock Market Efficiency', 'momentum'),
 ('Fads, Martingales, and Market Efficiency', 'reversal'),
 ('Does the Stock Market Overreact?', 'reversal'),
 ('When Are Contrarian Profits Due to Stock Market Overreaction?', 'reversal'),
 ('The 52-Week High and Momentum Investing', 'high'),
 ('Momentum Crashes', 'momentum_risk'),
 ('Momentum Has Its Moments', 'momentum_risk'),
 ('Value and Momentum Everywhere', 'value_momentum'),
 ('A Century of Evidence on Trend-Following Investing', 'trend'),
 ('A Quantitative Approach to Tactical Asset Allocation', 'moving_average'),
 ('Do Industries Explain Momentum?', 'momentum'),
 ('Profitability of Momentum Strategies: An Evaluation of Alternative Explanations', 'momentum'),
 ('Market States and Momentum', 'momentum_risk'),
 ('The High-Volume Return Premium', 'volume'),
 ('Price Momentum and Trading Volume', 'volume'),
 ('Trading Volume and Serial Correlation in Stock Returns', 'volume_reversal'),
 ('Illiquidity and stock returns: cross-section and time-series effects', 'liquidity'),
 ('Liquidity Risk and Expected Stock Returns', 'liquidity'),
 ('Liquidity as an Investment Style', 'liquidity'),
 ('Evaporating Liquidity', 'reversal'),
 ('Short-Term Reversals, Returns to Liquidity Provision, and the Costs of Immediacy', 'reversal'),
 ('Short-Term Reversals: The Effects of Past Returns and Institutional Exits', 'flows'),
 ('Volatility-Managed Portfolios', 'volatility'),
 ('On the performance of volatility-managed portfolios', 'volatility'),
 ('Risk Everywhere: Modeling and Managing Volatility', 'volatility'),
 ('Betting Against Beta', 'beta'),
 ('The Volatility Effect: Lower Risk without Lower Return', 'low_volatility'),
 ('Benchmarks as Limits to Arbitrage: Understanding the Low-Volatility Anomaly', 'low_volatility'),
 ('The Cross-Section of Volatility and Expected Returns', 'low_volatility'),
 ('Do ETFs Increase Volatility?', 'etf_ownership'),
 ('Exchange Traded Funds and Asset Return Correlations', 'etf_correlation'),
 ('Is there a dark side to exchange traded funds? An information perspective', 'etf_information'),
 ('Intraday arbitrage between ETFs and their underlying portfolios', 'etf_arbitrage'),
 ('ETF arbitrage under liquidity mismatch', 'etf_arbitrage'),
 ('ETF Arbitrage and Return Predictability', 'flows'),
 ('Arbitrage and Liquidity: Evidence from a Panel of Exchange Traded Funds', 'etf_arbitrage'),
 ('Are the flows of exchange-traded funds informative?', 'flows'),
 ('Price pressures', 'liquidity'),
 ('Market intraday momentum', 'intraday'),
 ('Overnight Returns and Firm-Specific Investor Sentiment', 'overnight'),
 ('The Overnight Return, One More Anomaly', 'overnight'),
 ('A Tug of War: Overnight Versus Intraday Expected Returns', 'overnight'),
 ('In Search of Attention', 'attention'),
 ('The Sum of All FEARS Investor Sentiment and Asset Prices', 'sentiment'),
 ('Investor Sentiment and the Cross-Section of Stock Returns', 'sentiment'),
 ('Stock Return Predictability and Variance Risk Premia: Statistical Inference and International Evidence', 'variance_premium'),
 ('Risk Premium Information from Treasury-Bill Yields', 'macro'),
 ('The Pre-FOMC Announcement Drift', 'macro'),
 ('Simple Technical Trading Rules and the Stochastic Properties of Stock Returns', 'technical'),
]


def get_json(url):
    for attempt in range(3):
        try:
            with urlopen(Request(url, headers={'User-Agent': 'ETFResearchLab/0.1 (local academic literature audit)'}), timeout=40) as r:
                return json.load(r)
        except Exception:
            if attempt == 2:
                raise
            time.sleep(5 * (attempt + 1))


def normalize(s):
    return re.sub(r'[^a-z0-9]', '', s.lower())


def resolve(item):
    i, (title, family) = item
    direct = VERIFIED_DOIS.get(i)
    key = hashlib.sha256(title.encode()).hexdigest()[:8]
    path = RESEARCH / 'sources' / (f'P{i:02d}_verified.json' if direct else f'P{i:02d}_{key}_crossref.json')
    path.parent.mkdir(parents=True, exist_ok=True)
    url = 'https://api.crossref.org/works?' + urlencode({'query.title': title, 'rows': 5})
    if direct:
        url = 'https://api.crossref.org/works/' + direct
    old = RESEARCH / 'sources' / f'P{i:02d}_crossref.json'
    if not direct and old.exists() and i not in {36,39,42,47,48} and not path.exists():
        path.write_bytes(old.read_bytes())
    if path.exists():
        raw = json.loads(path.read_text(encoding='utf-8'))
    else:
        time.sleep(1.2)
        raw = get_json(url)
        path.write_text(json.dumps(raw, indent=2), encoding='utf-8')
    def score(w):
        return difflib.SequenceMatcher(None, normalize(title), normalize(w.get('title', [''])[0])).ratio()
    works = [raw['message']] if direct else sorted(raw['message']['items'], key=score, reverse=True)
    best = works[0]
    return {'id': f'P{i:02d}', 'query_title': title, 'family': family,
            'match_score': score(best), 'title': best.get('title', [''])[0],
            'doi': best.get('DOI'), 'authors': [' '.join([a.get('given', ''), a.get('family', '')]).strip() for a in best.get('author', [])],
            'publication_date': best.get('published', {}).get('date-parts'),
            'publication_type': best.get('type'), 'journal': best.get('container-title'),
            'abstract': re.sub('<[^>]+>', '', best.get('abstract', '')),
            'source_url': url, 'url': best.get('URL'), 'links': best.get('link', []),
            'source_file': str(path.relative_to(ROOT)),
            'source_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def main():
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        records = list(pool.map(resolve, enumerate(CANDIDATES, 1)))
    (RESEARCH / 'catalog_metadata.json').write_text(json.dumps(records, indent=2), encoding='utf-8')
    for r in records:
        print(r['id'], round(r['match_score'], 3), r['doi'], r['title'].encode('ascii', 'replace').decode(), flush=True)


if __name__ == '__main__':
    main()
