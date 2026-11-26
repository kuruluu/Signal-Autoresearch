"""Candidate screening and lawful full-text attempts for the second literature round."""
import argparse
import concurrent.futures
import csv
import json
from .catalog import ROOT, RESEARCH
from .sources import PUBLIC, fetch_paper

OUT=RESEARCH/'expansion_001'
FAMILY={
 'trend':('High','Daily total-return prices support hypotheses; original futures excess returns, financing and roll histories may be missing.','Compare own-return sign, moving averages and sizing controls; several-day execution is an adaptation.'),
 'momentum':('Medium','Stock-level return, earnings, analyst, industry or factor data depend on the paper; ETF prices alone are not sufficient for all mechanisms.','Potential ETF rank or trend adaptation; audit source horizon and weighting before coding.'),
 'reversal':('High','Original stock universe, delistings and microstructure/cost filters are missing.','Audit short-horizon construction; ETFs require a distinct long-only adaptation.'),
 'etf':('High for data research','Historical ownership, constituent baskets, NAV, primary flows, trade/quote data and their availability timestamps may be required.','ETF-native mechanism; do not substitute traded volume for primary-market flows.'),
 'flows':('High for data research','Historical fund holdings, flows and their release timestamps are not in the current daily-price panel.','Resolve data and reporting lags before testing price-pressure hypotheses.'),
 'liquidity':('Medium','Bid/ask, transactions, liquidity measures and original universes usually exceed current price/volume coverage.','Separate liquidity measurement from a tradeable forecast and stress execution costs.'),
 'volatility':('Medium','Original equity returns, risk-free rates and exact variance model require audit.','Useful sizing/forecasting controls; positive expected return is not guaranteed.'),
 'cross_asset':('Medium','Cross-market prices, currencies or economic links require original timing/alignment audit.','ETF cross-market hypothesis possible only after defining available information.'),
 'allocation':('Control','Original portfolio universes and covariance/estimation procedures need audit.','Use as allocation baselines, not independent return signals.'),
 'technical':('Medium','Exact rules, searched parameter family, prices and cost assumptions need audit.','Avoid selecting attractive rules after viewing their results.'),
 'methodology':('Methods','No independent tradeable signal asserted.','Improve inference, multiple-testing and replication controls; not a strategy winner.'),
 'theory':('Mechanism','Belief formation and theoretical assumptions do not directly supply observed trade inputs.','Economic motivation only until a measurable causal signal is specified.')}

def main(fetch=False):
    records=json.loads((OUT/'candidates.json').read_text(encoding='utf-8'))
    prior=json.loads((RESEARCH/'papers.json').read_text(encoding='utf-8'))
    assert len(records)==50 and len({r['doi'].lower() for r in records+prior})==100
    path=OUT/'fulltext_access.json'
    if fetch:
        PUBLIC.update({
          'P53':'https://arxiv.org/pdf/1404.3274',
          'P54':'https://images.aqr.com/-/media/AQR/Documents/Insights/Journal-Article/AQR-Trends-Everywhere_JOIM.pdf?sc_lang=en',
          'P94':'https://www.cfr-cologne.de/download/workingpaper/cfr-21-04.pdf'})
        access=[]
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            for r in pool.map(fetch_paper,records):
                if r.get('full_text_accessible'):
                    txt=(RESEARCH/'fulltext'/f"{r['id']}.txt").read_text(encoding='utf-8')
                    r['extracted_characters']=len(txt)
                    r['extraction_requires_review']=len(txt)<2000
                access.append(r)
                path.write_text(json.dumps(access,indent=2),encoding='utf-8')
                print(r['id'],r['full_text_accessible'],flush=True)
    access={r['id']:r for r in json.loads(path.read_text())} if path.exists() else {}
    for r in records:
        priority,blocker,relevance=FAMILY[r['family']]
        r.update(priority=priority,required_data_and_blocker=blocker,etf_relevance=relevance,
                 review_depth='Bibliographic and prospective feasibility screening; source abstract available' if r.get('abstract') else 'Bibliographic and prospective feasibility screening; no abstract in metadata',
                 original_holding_horizon='Not verified from full methods; do not infer from the family',
                 publication_status='Working-paper record; publication status needs further checking' if 'ssrn' in r['doi'] or r['publication_type']!='journal-article' else 'Journal article record; peer-review process not independently audited',
                 full_text_access=access.get(r['id'],{'full_text_accessible':False,'attempts':[],'status':'Not attempted'}))
        if r['id']=='P54':
            r.update(publication_status='Published in Journal of Investment Management 18(1), 2020, pp.52-68; SSRN DOI is an earlier version, counted once',
                     canonical_publication_url='https://joim.com/year/2020/',canonical_publication_year=2020)
        if r['id'] in {'P51','P52'}:
            r['implementation_status']='Mechanism motivates trend_followup_001; ETF adaptation, not paper replication'
            r['review_depth']='Publisher abstract and bibliographic review; exact full methods not audited'
        if r['id']=='P51':
            r['reported_findings']='Publisher abstract attributes much of futures trend performance to volatility scaling; motivates always-long sizing controls. Not independently replicated.'
        if r['id']=='P52':
            r['reported_findings']='Publisher abstract distinguishes return-sign and moving-average rules and reports earlier MA signals in its sample. ETF experiment is not that original sample.'
        if r['id']=='P98':
            r['publication_timing_note']='Published after 2023; any test on current cached history would be retrospective, not post-publication confirmation.'
    (OUT/'reviewed_candidates.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
    fields=['id','candidate_id','title','authors','doi','url','publication_date','publication_status','family','priority',
            'review_depth','sample_period','original_holding_horizon','etf_relevance','required_data_and_blocker','implementation_status']
    with (OUT/'candidates.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for r in records:
            writer.writerow({k:'; '.join(r[k]) if k=='authors' else r.get(k,'') for k in fields})
    print('50 screened candidates; total 100 unique DOIs; new PDFs',sum(r['full_text_access']['full_text_accessible'] for r in records))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--fetch',action='store_true')
    main(parser.parse_args().fetch)
