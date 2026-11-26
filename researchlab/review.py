"""Human-authored feasibility notes joined to verified bibliographic records."""
import json
from .catalog import RESEARCH, ROOT
from .signals import SIGNALS
from .experiment import save

# horizon | original market/data | signal/mechanism | evidence summary
NOTES = '''
P01|1-12 months|58 futures/forwards across asset classes; excess returns, financing and contract rolls|Own past return predicts subsequent direction; underreaction then reversal|Reports persistence across instruments; daily ETF adaptation is a different experiment.
P02|3-12 months|US stocks; point-in-time returns, universe and delisting data|Buy relative winners and short relative losers|Reports positive winner-minus-loser returns; market exposure alone does not explain the reported finding.
P03|About one week|NYSE/AMEX individual stocks; CRSP daily returns|Buy recent losers and sell winners; short-horizon reversal|Reports weekly reversal after several microstructure and cost corrections in the working-paper copy.
P04|Several years|US stocks; CRSP monthly returns|Long-horizon losers versus winners; overreaction|Reports loser outperformance and January effects; a five-day ETF hold is a severe horizon change.
P05|Weekly|US stocks; individual and portfolio return lead-lag structure|Contrarian profits can arise through cross-autocorrelation|Warns that profitable contrarian trading does not uniquely establish stock-level overreaction.
P06|Monthly momentum horizon|US stocks; trailing highs and returns|Price proximity to the 52-week high; anchoring|Abstract reports predictive value beyond past returns and a distinction from long-run reversal.
P07|Momentum and crash episodes|Long-short momentum portfolios, market-state and volatility histories|Conditional momentum crash risk|Retain as risk-model reference; no independent crash-timing rule is claimed without a full equation audit.
P08|Risk-managed momentum|Daily long-short momentum portfolio returns|Scale momentum exposure using its predictable risk|Publisher summary reports substantial improvement from managing momentum crash exposure.
P09|Months|Multiple markets; value fundamentals and momentum measures|Combine value and momentum across asset classes|Abstract reports common factors and negative value-momentum correlation; value inputs are missing here.
P10|Months and long history|Century-scale cross-asset futures and historical market series|Diversified multi-horizon trend following|Full results not audited from retrieved metadata; implementation is an explicit trend hypothesis, not a replication.
P11|Monthly timing|Asset-class total-return indexes and cash returns|Moving-average tactical allocation|Author describes a simple timing model; monthly execution, index histories and original specification remain unaudited.
P12|Months|US stock and industry portfolios; industry memberships|Industry momentum versus individual-stock momentum|Abstract attributes substantial individual-stock momentum to industry components.
P13|Months to years|US stocks including later-period samples|Out-of-sample persistence and explanations of momentum|Abstract reports continuation in the 1990s and some evidence of eventual reversal.
P14|Monthly conditional momentum|US stocks and market return histories|Momentum conditioned on market state|Abstract reports stronger momentum following positive market returns; original states differ from our one-year gate.
P15|Day/week event, following month|US stocks; volume and event histories|Extreme volume attracts attention and subsequent demand|Abstract reports higher subsequent returns following unusually high volume.
P16|Months to years|US stocks; share turnover, returns and firm characteristics|Volume interacts with momentum persistence and reversal|Abstract reports that past turnover helps explain momentum and long-run reversal; raw volume is not share turnover.
P17|Daily|Stock market indexes and large stocks; daily volume/returns|High-volume price declines can reflect liquidity demand|Paper predicts greater expected returns after high-volume declines and decreasing autocorrelation with volume.
P18|Monthly/yearly relations from daily inputs|US stocks; daily returns and dollar volume|Absolute return / dollar volume as illiquidity proxy|Publisher abstract reports positive expected illiquidity premium and negative contemporaneous response to unexpected illiquidity.
P19|Monthly|US stock returns and estimated aggregate liquidity shocks|Exposure to liquidity innovations is priced|Abstract links higher expected stock returns with sensitivity to aggregate liquidity; level ranking is not a replication.
P20|Long-run style portfolios|US stocks; shares outstanding, turnover, firm styles|Low turnover as a distinct liquidity investment style|Publication summary treats turnover-based liquidity as distinct from size, value and momentum; shares outstanding unavailable here.
P21|Daily/short-term reversal|US stock/industry returns, bid-ask data and VIX|Liquidity-provision returns vary with stress|Paper reports stronger reversal returns in high-VIX periods; realized volatility proxy cannot verify that VIX mechanism.
P22|Fund returns and short reversals|Mutual funds, holdings/trades and stock returns|Separate liquidity supply and demand costs|Working-paper abstract finds fund costs of immediacy materially affect measured performance; no holdings data here.
P23|Monthly reversal over following two months|US stocks and institutional participation histories|Prior quarterly losses and institutional exits condition reversals|Abstract links stronger reversals after losses to reduced institutional liquidity provision.
P24|Monthly scaling with daily variance inputs|Equity factors, currency carry and daily factor returns|Inverse lagged realized variance scales factor exposure|Paper reports improved factor Sharpe ratios and alphas; capped long-only ETF inverse variance changes both assets and leverage.
P25|Out-of-sample volatility management|Factor strategy return panel|Challenge practical implementation of volatility-managed portfolios|Publisher summary distinguishes attractive spanning regressions from weights implementable in real time; retained as counterevidence.
P26|High-frequency forecasts and portfolio horizons|High-frequency returns across over 50 assets|Pool volatility information within/across asset classes|Abstract reports improved forecasts; cannot reproduce high-frequency realized measures from daily ETF bars.
P27|Factor portfolio horizon|Stocks, bonds and futures; beta, financing, short availability|Levered low-beta long versus high-beta short|Publisher reports a BAB premium consistent with financing constraints; our long-only beta ranking is not BAB.
P28|Long-run low-risk portfolios|Global equities; stock volatilities and risk factors|Low-volatility portfolios and leverage constraints|Public research summary reports low-volatility risk-adjusted outperformance; cross-asset ETFs introduce an asset-allocation confound.
P29|Long-run stock portfolios|US stocks and benchmark-relative incentives|Benchmark constraints as a mechanism for low-risk anomaly|Metadata establishes the topic; detailed empirical conclusions and original controls need full-text verification.
P30|Monthly cross section|US stocks; market/factor returns, daily residual volatility|Idiosyncratic volatility and future returns|Original factor specification is not verified here; single-SPY residual risk is only an exploratory adaptation.
P31|Daily/intraday, ownership and index changes|ETF holdings, stock returns, index reconstitution, lending and trading costs|ETF ownership propagates liquidity shocks through arbitrage|Working paper reports higher volatility for ETF-owned stocks; not a direct executable ETF price rule.
P32|Daily and constituent comovement|US ETF holdings, activity and underlying stock returns|ETF arbitrage links constituent returns|Abstract reports ETF activity and return comovement, with stronger effects in small/illiquid stocks.
P33|Ownership changes and pricing efficiency|ETF holdings, analyst coverage, earnings and stock microstructure|ETF ownership changes incentives for information acquisition|Author/publisher evidence links ownership to higher trading costs and less informative underlying prices.
P34|Minute-by-minute plus daily tests|ETF/constituent quotes and order imbalances|Test the direction of ETF arbitrage price discovery|Publisher abstract finds little evidence that ETF trading leads underlying prices; important counterevidence to simple shock narratives.
P35|Intraday/daily arbitrage under stress|Bond ETFs, constituent bonds, AP inventories and liquidity|Liquidity mismatch constrains authorized-participant arbitrage|Detailed empirical findings not verified in retrieved full text; daily prices alone cannot identify the mechanism.
P36|Subsequent ETF returns|ETF primary-market creations/redemptions and returns|Observable arbitrage proxies for non-fundamental demand|Public working-paper abstract reports that arbitrage activity negatively predicts subsequent returns.
P37|Intraday liquidity and adjustment|Equity/bond ETF trade-level observations and constituents|Liquidity determines speed and efficacy of arbitrage|Paper reports weaker arbitrage for less liquid instruments and liquidity spillovers in bond ETFs.
P38|Next day|Daily ETF flows, market demand, arbitrage opportunities and news|Unexpected component of ETF flows|Abstract reports next-day return and news predictability from unexpected flows; point-in-time flow timestamps are essential.
P39|Daily with short decay|NYSE intermediary inventories and stock prices|Inventory pressure induces temporary price deviations|Author/publisher summary supports transitory inventory-related price pressure; dealer inventories are unavailable here.
P40|First to last half-hour|SPY and other ETF intraday observations|Opening-half-hour market return forecasts closing-half-hour return|Author abstract reports intraday momentum, stronger on volatile/high-volume/news days; daily OHLC cannot test this.
P41|Weekly persistence, longer reversal|US stocks; CRSP open/close and firm characteristics|Overnight return as firm-specific sentiment|Paper reports short-run overnight persistence and longer-run reversal; holding ETFs all day changes the target.
P42|Overnight and next intraday|Stock opens/closes and execution conditions|Overnight/intraday return relationship|Working-paper abstract describes an overnight anomaly; complete execution rule and sampling assumptions unverified.
P43|Overnight versus intraday|Stock returns split by trading session|Different investor clienteles and opposing session returns|Metadata verified; full empirical decomposition must be reviewed before implementing a session-specific strategy.
P44|Weeks and longer reversals|Google search-volume indices and stock returns|Search intensity measures retail attention|Paper proposes search volume as direct attention measure; price/volume alone cannot faithfully reproduce it.
P45|Short horizon sentiment|Search-query history and asset returns|FEARS search-based sentiment index|Metadata verified; keyword dictionary, vintage data and normalization must be recovered before a faithful test.
P46|Monthly cross section|Sentiment proxies and stock characteristics|Sentiment affects hard-to-value/hard-to-arbitrage stocks|Abstract reports conditional differences in subsequent returns across speculative stock characteristics.
P47|Two to four months|International option-implied and realized variance, index returns|Variance risk premium forecasts equity returns|Public paper reports predictive relations and Monte Carlo checks for overlapping-return inference; realized variance alone is insufficient.
P48|Below a quarter and over one year|Point-in-time Treasury bill/bond yield curves|Short and long components of risk-premium information|Abstract reports short-maturity bills contain information not spanned by long yields; ETF prices do not supply these yield vintages.
P49|24 hours before scheduled FOMC announcements|Historical announcement timestamps and intraday index returns|Pre-announcement equity return drift|Abstract reports a large pre-FOMC component of historical equity returns; exact event-time scheduling required.
P50|Daily technical rules|Historical Dow Jones index prices|Moving averages and trading-range breakouts|Abstract reports support for technical rules under several null models; historical daily-index execution and data-snooping remain concerns.
'''

SAMPLES = {'P01':'January 1985-December 2009 (main futures results; full text)',
 'P03':'July 1962-December 1986 (downloaded 1988 working paper)',
 'P14':'1929-1995 (abstract)', 'P21':'January 1998-December 2010 (downloaded working paper tables)',
 'P40':'1993-2013 SPY (author working-paper abstract)',
 'P41':'July 1992-December 2013 (full-text main sample; some tables mention June 1992)',
 'P47':'January 2000-December 2010 (downloaded working paper)', 'P50':'1897-1986 (abstract)'}


def main():
    metadata = json.loads((RESEARCH/'catalog_metadata.json').read_text(encoding='utf-8'))
    access = {r['id']:r for r in json.loads((RESEARCH/'fulltext_access.json').read_text())}
    notes = {parts[0]:parts[1:] for line in NOTES.strip().splitlines() if (parts:=line.split('|'))}
    mapped = {p:[s for s in SIGNALS if p in s.papers] for p in notes}
    records=[]
    for r in metadata:
        pid=r['id']
        horizon, data, mechanism, finding = notes[pid]
        specs=mapped[pid]
        status='ETF adaptation tested; original replication blocked' if specs else 'Blocked; feasibility assessed, no synthetic substitute'
        if pid in {'P07','P25'}:
            status='Risk/methodology reference; no independent signal tested'
        peer='Working paper / preprint' if r['doi'].startswith(('10.2139','10.17016','10.3386')) else 'Published journal article (peer-review quality not independently audited)'
        record={**r, 'publication_status':peer, 'full_text_access':access[pid],
            'review_depth':'Downloaded source and targeted methods/abstract review' if access[pid]['full_text_accessible'] else
                          ('Abstract and feasibility review; full methods unavailable' if r['abstract'] else 'Metadata plus available author/publisher summaries; methods incomplete'),
            'original_market_and_data':data, 'original_sample_period':SAMPLES.get(pid,'Not verified from inspected source sections; do not infer dates'),
            'original_horizon':horizon,'signal_and_economic_rationale':mechanism,'reported_findings_and_limits':finding,
            'direct_etf':pid in {'P31','P32','P33','P34','P35','P36','P37','P38','P40'},
            'implementation_status':status,'adaptation_ids':[s.id for s in specs],
            'adaptation_changes':[s.adaptation for s in specs],
            'replication_status':'NOT replicated',
            'implementation_attempt':'Mapped required observations and timing to available daily ETF panel. '+
                ('Implemented separate ETF hypothesis with explicit changed assumptions.' if specs else 'No faithful implementation possible with current inputs; kept out of numerical ranking.'),
            'blocker':'Original data/universe and exact filters, portfolio construction, costs and statistical tests are not fully audited. Required inputs: '+data,
            'quality_assessment':'Publication is not proof. Original universe, transaction costs, dependence, multiple searches, publication bias and ETF transferability need separate assessment.',
            'evidence_files':[r['source_file']] + ([f'research/fulltext/{pid}.txt'] if access[pid]['full_text_accessible'] else []),
            'ambiguities':['Paper and public working-copy versions can differ.','Unknown sample dates remain unknown.',
                           'Five-day, long-only ETF hypotheses cannot validate the original stock/futures/event mechanism.']}
        if pid=='P28':
            record['bibliographic_note']='Crossref short title is The Volatility Effect; subtitle and authors checked against Erasmus research record.'
        if pid=='P36':
            record['bibliographic_note']='Canonical 2021 publication supersedes the earlier ETF Arbitrage and Return Predictability working paper; counted once.'
        records.append(record)
    assert len(records)==50 and len({r['doi'].lower() for r in records})==50
    save(RESEARCH/'papers.json',records)
    import csv
    fields=['id','title','authors','publication_date','doi','url','publication_status','family','direct_etf','review_depth',
            'original_market_and_data','original_sample_period','original_horizon','signal_and_economic_rationale',
            'reported_findings_and_limits','implementation_status','adaptation_ids','blocker']
    with (RESEARCH/'papers.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=fields)
        writer.writeheader()
        for r in records:
            writer.writerow({k:r[k] for k in fields})
    folder=RESEARCH/'paper_records'
    folder.mkdir(exist_ok=True)
    for r in records:
        (folder/(r['id']+'.txt')).write_text('\n\n'.join(f'{k}: {json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v}' for k,v in r.items() if k!='abstract'),encoding='utf-8')
    print('50 paper records; adaptations cover',sum(bool(r['adaptation_ids']) for r in records),'papers')


if __name__=='__main__':
    main()
