"""Standalone report and durable continuation appendix; original results unchanged."""
import html
import json
from collections import Counter
from .catalog import ROOT, RESEARCH
from .integrity import sha, verify

OUT=RESEARCH/'expansion_001'
MARKER='CONTINUATION 001 — 50 ADDITIONAL CANDIDATES AND TREND CONTROLS'

def main():
    verify()
    candidates=json.loads((OUT/'reviewed_candidates.json').read_text(encoding='utf-8'))
    exp=OUT/'trend_experiment'
    metrics=json.loads((exp/'metrics.json').read_text())
    contrasts=json.loads((exp/'contrasts.json').read_text())
    completion=json.loads((exp/'completion.json').read_text())
    names={'E01':'Always long / equal slots','E02':'Positive one-year return / equal slots',
           'E03':'Above one-year average / equal slots','E04':'Always long / inverse volatility',
           'E05':'Positive one-year return / inverse volatility','E06':'Above one-year average / inverse volatility'}
    downloaded=sum(r['full_text_access']['full_text_accessible'] for r in candidates)
    counts=Counter(r['family'] for r in candidates)
    new_checks=[]
    for r in candidates:
        actual=sha(ROOT/r['source_file'])
        assert actual==r['source_sha256'],r['id']
        new_checks.append({'id':r['id'],'path':r['source_file'],'sha256':actual})
        a=r['full_text_access']
        if a['full_text_accessible']:
            path=RESEARCH/'fulltext'/f"{r['id']}.pdf"
            assert sha(path)==a['pdf_sha256'],r['id']
            new_checks.append({'id':r['id'],'path':str(path.relative_to(ROOT)),'sha256':sha(path)})
    (OUT/'new_source_integrity.json').write_text(json.dumps(new_checks,indent=2),encoding='utf-8')
    lines=[MARKER,
      'Anchor assumption: P01 Time series momentum, following the immediately preceding discussion. Expansion also includes ETF-native and liquidity research.',
      f'50 new bibliographic candidates; 100 total unique DOI records across original and expansion catalogs. {downloaded} additional full texts retrieved, not full methods audits.',
      'Family counts: '+', '.join(f'{k}={v}' for k,v in sorted(counts.items())),
      'The set includes 10 methodological papers, two allocation controls and two theoretical papers; 50 candidates does NOT mean 50 executable signals.',
      'Original 231 variants and results preserved. 94 original integrity checks passed; 35 tests passed including three new causal/edge-case checks.',
      'Method audit: research/expansion_001/METHOD_AUDIT.txt. P01/P03/P24 constructions compared with code; P36/P37 inputs and formulas clarified. Flow-data access remains unresolved.',
      'Important correction: original S01 selects top-three positive-return ETFs. It does not simply trade every positive own-return sign. Existing artifacts remain as historical records.',
      'New experiment: research/expansion_001/trend_experiment/registration.json; registered before this run, after earlier history had already been examined.',
      'Six portfolio arms, 36 new variants, 72 period evaluations, 24 paired contrasts. Joint family has 291 comparisons per period (231 previous +36 new +24 contrasts).',
      '2000 synchronized stationary bootstrap paths at block lengths 10,20,40; conservative paper-count floor increased to 100 for this follow-up only.',
      'Periods 2019-2020 and 2021-2023 are USED exploratory evidence, never new validation. No final 2024-2025 observations downloaded or evaluated.',
      'Controls use the same sizing formula, engine constraints and trade schedule; actual exposure and risk differ. Differences are not pure alpha.',
      f'Exploratory eligible directional arms: {completion["exploratory_eligible"]}; confirmed successes: 0.',
      'Base control-relative annualized mean DAILY return differences (percentage points; NOT differences in CAGR):']
    for r in contrasts:
        if r['variant']=='base':
            lines.append(f"{r['arm']} minus {r['control']} | {r['period']} | {100*r['mean_difference_annualized']:+.3f} pp/year | corrected p (block20)={r['bootstrap']['20']['p_conservative']:.4f}")
    lines += ['', 'INTERPRETATION',
      'No newly established successful-signal similarity. Return-sign and average-price filters share trend inputs, but control-relative return differences change sign across the two periods. Sizing can alter apparent ranking; these observations motivate controls, not a claim that volatility scaling causes alpha.',
      'Failure of these ETF rules does not refute the original futures papers. Horizons, direction constraints, costs, cash yield, universe and estimator all differ.',
      '', 'REPRODUCTION',
      '.\\research.ps1 audit', '.\\research.ps1 test', '.\\research.ps1 expand', '.\\research.ps1 expand-sources',
      '.\\research.ps1 followup', '.\\research.ps1 expansion-report',
      'Candidate discovery reruns must preserve the frozen candidates.json hash used by registration. New definitions need a new experiment directory/version.',
      '', 'NEXT CODEX PROMPT',
      'Read this continuation, research/expansion_001/METHOD_AUDIT.txt, reviewed_candidates.json, trend_experiment/registration.json, assessment.json and integrity.json. Preserve both result sets and verify hashes. All history through 2023 is used. No 2024-2025 downloads or evaluation without explicit release protocol and permanent consumption record. Do not buy data or submit trades.',
      'Prioritize complete methods and source data for P51/P52, then exact horizons and available data for P65 (short-run return predictability), P63 (residual momentum), and ETF-native P36/P37/P94/P95. Candidate IDs have gaps because rejected search matches are retained in screening.json. Resolve reporting timestamps for NAV/shares/flows. No volume-as-flow proxy.',
      'Register every new variant and comparison before measuring returns. Include all prior and new tested alternatives in search accounting; do not tune gates to obtain a winner. If testing risk-adjusted utility or drawdown reduction, predefine that different objective and comparator. Current max-T bootstrap does not eliminate adaptive human search bias.',
      'Update exact source versions, findings, hypotheses, blockers and consumed periods. An inaccessible full text is not a completed review. A positive backtest is not a faithful replication.',
      '', 'NEW CANDIDATE INDEX']
    lines += [f"{r['id']} | {r['title']} | {', '.join(r['authors'])} | https://doi.org/{r['doi']} | {r['family']} | {r['priority']}" for r in candidates]
    appendix='\n'.join(lines)+'\n'
    (OUT/'HANDOFF_APPENDIX.txt').write_text(appendix,encoding='utf-8')
    target=ROOT/'SIGNAL_RESEARCH_HANDOFF.txt'
    original=target.read_text(encoding='utf-8').split(MARKER)[0].rstrip()
    current_handoff=RESEARCH/'replication_first'/'HANDOFF.txt'
    handoff=current_handoff.read_text(encoding='utf-8') if current_handoff.exists() else original+'\n\n'+appendix
    target.write_text(handoff,encoding='utf-8')
    similar=ROOT/'SIGNAL_SIMILARITIES.txt'
    old=similar.read_text(encoding='utf-8').split(MARKER)[0].rstrip()
    similar.write_text(old+'\n\n'+MARKER+'\nNo additional successful signals established. '+
        'All four trend-versus-control differences changed sign between used periods. All base block-20 corrected p-values were 1.0. '+
        'Shared trend inputs and sensitivity to sizing are hypotheses, not independent corroboration of an edge. '+
        'See research/expansion_001/trend_experiment/contrasts.json and assessment.json.\n',encoding='utf-8')
    esc=html.escape
    rows=[]
    for r in metrics:
        if r['variant']!='base':continue
        contrast=next((c for c in contrasts if c['arm']==r['arm'] and c['period']==r['period'] and c['variant']=='base'),None)
        delta=f"{contrast['mean_difference_annualized']*100:+.2f} pp" if contrast else 'Control'
        pv=f"{contrast['bootstrap']['20']['p_conservative']:.3f}" if contrast else '—'
        rows.append(f"<tr><td>{esc(names[r['arm']])}</td><td>{r['period'].replace('used_','')}</td><td>{r['net_cagr']:.2%}</td><td>{r['mean_exposure']:.1%}</td><td>{delta}</td><td>{pv}</td></tr>")
    papers=[]
    for r in candidates:
        full=r['full_text_access']['full_text_accessible']
        pdf=f'<a href="../fulltext/{r["id"]}.pdf">Local PDF</a>' if full else 'Full text not retrieved'
        papers.append(f'''<details data-family="{esc(r['family'])}"><summary>{r['id']} · {esc(r['title'])}</summary>
<p>{esc('; '.join(r['authors']))}</p><p>{esc(r['publication_status'])}</p>
<p><a href="https://doi.org/{esc(r['doi'])}">Source</a> · {pdf} · {esc(r['family'])} · Priority: {esc(r['priority'])}</p>
<p>{esc(r['etf_relevance'])}</p><p>Data/method blocker: {esc(r['required_data_and_blocker'])}</p>
<p>Review: {esc(r['review_depth'])}. Original sample and exact holding horizon remain unaudited unless separately stated.</p></details>''')
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ETF research — 50 additional candidates</title><style>
body{font:16px system-ui;max-width:1200px;margin:32px auto;padding:0 20px;background:#101923;color:#e4edf5;line-height:1.55}a{color:#83dcc8}h1{line-height:1.15}p{color:#c2cfda}.note,details{background:#1c2a38;padding:16px;margin:12px 0;border-radius:8px}.note{border-left:4px solid #e4b66a}table{border-collapse:collapse;width:100%;font-size:14px}td,th{padding:10px;text-align:left;border-bottom:1px solid #435363}.scroll{overflow:auto}input,select{padding:12px;background:#243647;color:white;border:1px solid #65798a;margin-right:8px}summary{cursor:pointer}small{color:#b7c7d5}</style>
<h1>ETF research: the next 50 candidates</h1>
<p>100 distinct bibliographic records across both rounds. 50 new candidates screened; NEWPDF full texts retrieved in this round. Bibliographic screening is not full methods review.</p>
<div class="note"><b>No confirmed trading edge.</b> The follow-up used previously examined history through 2023. Final 2024–2025 observations remain sealed. The 50 candidates include methodological, allocation and theoretical references; they are not 50 newly backtested strategies.</div>
<p><a href="candidates.csv">50-candidate CSV</a> · <a href="reviewed_candidates.json">Detailed screening JSON</a> · <a href="METHOD_AUDIT.txt">Methods audit</a> · <a href="../../SIGNAL_RESEARCH_HANDOFF.txt">Updated handoff</a> · <a href="../dashboard.html">Original study</a></p>
<h2>Trend direction versus position sizing</h2><p>Six arms, 36 portfolio variants, 72 period evaluations. Four directional arms are compared with always-long controls using the same sizing rule and execution schedule. Realized risk and exposure differ. All four failed the registered follow-up gates.</p>
<p>2,000 synchronized block-bootstrap paths at each of three block lengths. Joint adjustment covers 291 comparisons, including the prior 231. The table shows base runs only; the full exports retain every variant.</p>
<div class="scroll"><table><thead><tr><th>Portfolio rule</th><th>Used period</th><th>Net CAGR</th><th>Mean exposure</th><th>Annual mean difference vs control</th><th>Adjusted p (20-day blocks)</th></tr></thead><tbody>ROWS</tbody></table></div>
<p><small>Mean return differences are annualized daily differences, not CAGR differences. Costs and execution remain modeled. Zero cash interest and a fixed surviving ETF universe limit interpretation.</small></p>
<p><a href="trend_experiment/registration.json">Frozen protocol</a> · <a href="trend_experiment/metrics.csv">All variant metrics</a> · <a href="trend_experiment/contrasts.json">All control comparisons</a> · <a href="trend_experiment/assessment.json">Gate results</a></p>
<h2>Candidate library</h2><p>Filter by title, author, topic or blocker. Several-day ETF relevance is a screening judgment, not a paper finding.</p>
<input id="query" aria-label="Search candidates" placeholder="Search candidates"><select id="family" aria-label="Filter by family"><option value="">All families</option>OPTIONS</select><p id="count">50 candidates</p><section id="papers">PAPERS</section>
<script>const q=document.getElementById('query'),f=document.getElementById('family');function filter(){let n=0;document.querySelectorAll('details').forEach(d=>{let yes=(!f.value||d.dataset.family===f.value)&&d.textContent.toLowerCase().includes(q.value.toLowerCase());d.hidden=!yes;n+=yes});document.getElementById('count').textContent=n+' candidates shown'}q.addEventListener('input',filter);f.addEventListener('change',filter);</script></html>'''
    page=page.replace('NEWPDF',str(downloaded)).replace('ROWS',''.join(rows)).replace('PAPERS',''.join(papers)).replace('OPTIONS',''.join(f'<option>{esc(k)}</option>' for k in sorted(counts)))
    (OUT/'report.html').write_text(page,encoding='utf-8')
    print('Expansion report, source checks and handoff updated')

if __name__=='__main__':main()
