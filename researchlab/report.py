"""Generate an offline dashboard and a self-contained next-session handoff."""
import html
import json
from collections import Counter
from pathlib import Path
import numpy as np
import pandas as pd
from .catalog import RESEARCH, ROOT
from .signals import SIGNALS
from .experiment import save
from .data import protocol


def conclusions(rows):
    lookup={(r['signal'],r['variant'],r['period']):r for r in rows}
    assessment=[]
    for s in SIGNALS:
        v=lookup[s.id,'base','validation']
        w=lookup[s.id,'base','walk_forward']
        checks={
          'positive_net_both':v['net_cagr']>0 and w['net_cagr']>0,
          'positive_active_both':v['active_mean_annualized']>0 and w['active_mean_annualized']>0,
          'bootstrap_lower_positive_both':all(r['bootstrap_block_20']['low_daily']>0 for r in [v,w]),
          'multiple_testing_both':all(r['bootstrap_block_20']['p_conservative']<=.05 for r in [v,w]),
          'cost_stress_active_positive':all(lookup[s.id,c,p]['active_mean_annualized']>0 for c in ['cost2x','cost4x'] for p in ['validation','walk_forward']),
          'positive_active_two_of_three_years':sum(y['active_mean']>0 for y in w['years'])>=2}
        assessment.append({'signal':s.id,'name':s.name,'family':s.family,'checks':checks,
                           'provisional_candidate':all(checks.values()),'robust_success':False,
                           'robust_success_blockers':['Final sample sealed','Fixed survivor universe','Adaptation rather than faithful replication']})
    return assessment


def main():
    p,_=protocol()
    papers=json.loads((RESEARCH/'papers.json').read_text(encoding='utf-8'))
    rows=json.loads((RESEARCH/'results/metrics.json').read_text())
    findings=conclusions(rows)
    save(RESEARCH/'results/success_assessment.json',findings)
    corr=pd.read_csv(RESEARCH/'results/walk_forward_active_correlation.csv',index_col=0)
    pairs=sorted([(float(corr.loc[a,b]),a,b) for i,a in enumerate(corr.index) for b in corr.columns[i+1:]
                  if np.isfinite(corr.loc[a,b])],reverse=True)
    counts={'papers_found':len(papers),'feasibility_reviewed':len(papers),
            'downloaded_full_texts':sum(r['full_text_access']['full_text_accessible'] for r in papers),
            'papers_with_abstract_metadata':sum(bool(r['abstract']) for r in papers),
            'distinct_adaptations':len(SIGNALS),'papers_with_adaptations':sum(bool(r['adaptation_ids']) for r in papers),
            'papers_without_numerical_adaptation':sum(not r['adaptation_ids'] for r in papers),
            'faithful_replications':0,'original_replications_blocked':50,
            'variant_experiments':len(rows)//2,'period_evaluations':len(rows),
            'provisional_candidates':sum(r['provisional_candidate'] for r in findings),'robust_successes':0}
    save(RESEARCH/'results/summary.json',counts)
    concentration=[]
    for s in SIGNALS:
        trades=pd.read_csv(RESEARCH/f'results/{s.id}_walk_forward_trades.csv')
        if len(trades):
            grouped=trades.groupby('symbol').net_pnl.sum()
            totalabs=trades.groupby('symbol').net_pnl.apply(lambda x:x.abs().sum())
            concentration.append({'signal':s.id,'net_pnl_by_symbol':grouped.to_dict(),
                                  'absolute_trade_pnl_share_by_symbol':(totalabs/totalabs.sum()).to_dict() if totalabs.sum() else {}})
    save(RESEARCH/'results/asset_concentration.json',concentration)
    curves={}
    for period in ['validation','walk_forward']:
        df=pd.read_csv(RESEARCH/f'results/{period}_equity_curves.csv',index_col=0)
        curves[period]={'dates':df.index.tolist(),'series':{c:df[c].tolist() for c in df.columns}}
    payload=json.dumps({'papers':[{k:v for k,v in r.items() if k!='abstract'} for r in papers],
                        'metrics':rows,'findings':findings,'counts':counts,'curves':curves},ensure_ascii=True).replace('<','\\u003c')
    page=TEMPLATE.replace('__DATA__',payload)
    (RESEARCH/'dashboard.html').write_text(page,encoding='utf-8')
    tested=[r for r in rows if r['period']=='walk_forward' and r['variant']=='base']
    ranked=sorted(tested,key=lambda r:r['net_cagr'],reverse=True)
    lines=[
      'SIGNAL RESEARCH HANDOFF - ETF Research Lab',
      'This is a local research artifact, not a deployment instruction or a verified trading edge.',
      f'Workspace: {ROOT}',
      '', 'OBJECTIVE AND CURRENT STATE',
      'Identify and compare 50 papers relevant to ETF signals and several-day holding horizons.',
      json.dumps(counts,indent=2),
      'Downloaded full texts are not equivalent to complete equation-by-equation replication reviews.',
      '50 papers were bibliographically and feasibility assessed; review depth and unverified sample dates are explicit per record.',
      'The original paperlab forward runner was inspected and preserved. researchlab uses no order API.',
      '', 'REPRODUCTION',
      'PowerShell: .\\research.ps1 test',
      'PowerShell: .\\research.ps1 catalog',
      'PowerShell: .\\research.ps1 sources',
      'PowerShell: .\\research.ps1 review',
      'PowerShell: .\\research.ps1 data',
      'PowerShell: .\\research.ps1 pilot',
      'PowerShell: .\\research.ps1 run',
      'PowerShell: .\\research.ps1 report',
      'Read research/README.md for installation and equivalent Python commands.',
      '', 'DATA AND PROVENANCE',
      '12 fixed surviving ETFs: '+', '.join(p['universe']),
      'Yahoo chart API observations: 2007-01-03 through 2023-12-29, 4278 common XNYS sessions.',
      'Raw JSON, extracted CSV, checksums and URLs: research/data/manifest.json. Corporate-action payloads remain in raw JSON.',
      'Adjusted open = raw open * adjusted close / raw close. Synthetic total-return units, not a cash-dividend share ledger.',
      'Calendar source: exchange_calendars XNYS; schedule includes UTC opens/closes and accounts for holidays/early closes/DST.',
      'Alpaca IEX is NOT used as a historical consolidated feed. No credentials or paid data purchased.',
      'Survivorship, revised data, approximate opening execution, zero cash yield and transaction-cost assumptions limit inference.',
      '', 'PROTOCOL AND IMPLEMENTATION',
      'Frozen protocol: research/protocol.json. Experiment/code hashes: research/results/registration.json.',
      'Definitions: researchlab/signals.py. Execution: researchlab/engine.py. Statistics: researchlab/bootstrap.py.',
      '21 signal hypotheses, each with 11 predeclared variants; all retained rather than selecting a winner.',
      'Base holds five exchange sessions; sensitivity holds 2/10. Additional cost2x/cost4x, delay1, 10% missed trades, lookback80/120%, equities/defensive subsets.',
      'Signal observes prior close; next open execution. Long-only, no leverage, 90% gross cap, 20% asset cap, 10% annual ex-ante risk ceiling.',
      'Complete nonoverlapping cohorts within splits; 10-session boundary gap. Cash starts fresh at each evaluation split.',
      'No predictive model fitting: rolling risk estimation uses past data. Walk-forward means fixed-rule chronological execution, not re-optimized machine learning.',
      'Primary benchmark: 90% equal-weight initial buy-and-hold of the same 12 ETFs; additional SPY/cash results saved. Different exposures mean raw active return is not pure alpha.',
      'Costs: 0 commission + 2bps half-spread + 3bps slippage per side; scenario assumptions, not observed bid/ask.',
      'Monte Carlo: 2000 synchronized stationary bootstrap resamples per period/block length (10/20/40 sessions), seed6413.',
      'Bootstrap is on aligned fixed-strategy active daily returns, preserving temporal blocks and contemporaneous cross-strategy dependence.',
      'Centered null + max studentized mean across all231variants, with conservative 50-paper Bonferroni floor. Not a refit bootstrap or proof against unrecorded searches.',
      'Paper-specific available samples and shared common periods are separate; related papers may map to the same signal and do not count as independent corroborations.',
      '', 'OBSERVED AND SEALED DATA',
      '2007-2016 history used for warmup/retrospective own-sample tests. 2017-2020 validation USED. Common validation2019-2020 starts after all implemented-paper publication dates.',
      '2021-2023 walk-forward USED for research evaluation. These results are now development evidence for any future modification.',
      '2024-2025 FINAL REMAINS SEALED: its daily bars were not downloaded or evaluated by this project.',
      'Never relabel used data as untouched. Do not tune to sealed data. Before releasing it, freeze hypotheses, log a new protocol and permanently mark the final period consumed.',
      'An initial pilot reporting bug (boolean regime mask) was fixed; failed artifacts retained in research/pilot_failed_001. No return-driven parameter tuning followed.',
      '', 'ESTABLISHED RESULTS',
      'Evidence: research/results/metrics.json, metrics.csv, success_assessment.json, *_daily.csv, *_trades.csv, *_regimes.json, asset_concentration.json.',
      f'Provisional candidates passing all predeclared gates: {counts["provisional_candidates"]}. Robust successes: 0.',
      'No successful-signal similarity is established. Absence of a winner here does not refute the original papers: these are changed instruments/horizons and exposures.',
      'Base walk-forward returns (descriptive, not a recommendation):',
    ]
    lines += [f"{r['signal']}: netCAGR={r['net_cagr']:.4%}; activeAnnualMean={r['active_mean_annualized']:.4%}; correctedP={r['bootstrap_block_20']['p_conservative']:.4f}" for r in ranked]
    lines += ['', 'TENTATIVE INTERPRETATIONS AND SIMILARITIES',
      'Top correlated active-return pairs from research/results/walk_forward_active_correlation.csv:',
      *[f'{a} / {b}: correlation={v:.3f}' for v,a,b in pairs[:8]],
      'These correlations are descriptive across ALL signals, not evidence about successful signals. Subtracting a shared benchmark itself induces dependence.',
      'Trend/momentum share price-persistence inputs. Reversal and volume rules share liquidity/attention hypotheses. Low-risk rules can primarily select bonds.',
      'No causal inference follows from these similarities. Compare counterexamples and exposures before choosing future experiments.',
      '', 'BLOCKED RESEARCH AND PRIORITIES',
      'Read research/papers.csv and paper_records/Pxx.txt for each exact blocker. Original replications require original universes and complete method audits.',
      'Priority1: Audit accessible full methods for the3pilot papers; acquire point-in-time ETF universe, distributions and consolidated historical quote data without purchasing until authorized.',
      'Priority2: Obtain historical NAV, creations/redemptions and publication timestamps for ETF-native flow/arbitrage papers P31-P38. Do not replace flows with trading volume.',
      'Priority3: Obtain intraday bars/quotes and event times for P40/P42/P43/P49; ordinary daily bars cannot establish these session effects.',
      'Priority4: Obtain search/sentiment, options-implied variance and yield vintages for P44-P48; avoid revised or retrospectively selected inputs.',
      'Priority5: Add exposure-matched/risk-factor controls in a newly registered experiment; do not silently change the primary benchmark of this run.',
      'Priority6: Pre-register combinations of economically distinct signals on used periods, account for every new trial, then consider a once-only final evaluation.',
      '', 'READY-TO-RUN FOLLOW-UP PROMPT',
      'Continue this ETF research project from this handoff. Read research/README.md, protocol.json, papers.json, results/registration.json, results/success_assessment.json, and observed_periods.json. Verify checksums and run tests. Preserve the current results. Resolve paper-specific data/method blockers, starting with the pilot full texts and ETF-native flow papers. Register any new variants before evaluating them. Treat every period through2023 as already examined. Do not read or download2024-2025 final observations without a new explicit release protocol and permanent consumption record. Never call an ETF proxy a faithful replication. Do not buy data or place real-money trades. Update this handoff with exact evidence paths and distinguish findings from hypotheses.',
      '', 'PAPER INDEX - deduplicated canonical publications',
    ]
    lines += [f"{r['id']} | {r['title']} | {', '.join(r['authors'])} | {r['url']} | {r['implementation_status']}" for r in papers]
    appendix = RESEARCH/'expansion_001'/'HANDOFF_APPENDIX.txt'
    handoff = '\n'.join(lines)
    if appendix.exists():
        handoff += '\n\n' + appendix.read_text(encoding='utf-8')
    current_handoff = RESEARCH/'replication_first'/'HANDOFF.txt'
    if current_handoff.exists():
        handoff = current_handoff.read_text(encoding='utf-8')
    (ROOT/'SIGNAL_RESEARCH_HANDOFF.txt').write_text(handoff,encoding='utf-8')
    (ROOT/'SIGNAL_SIMILARITIES.txt').write_text('\n'.join(lines[lines.index('ESTABLISHED RESULTS'):lines.index('BLOCKED RESEARCH AND PRIORITIES')]),encoding='utf-8')
    print(json.dumps(counts,indent=2))


TEMPLATE=r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ETF Signal Research Lab</title><style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#101923;color:#e4edf5;font:15px system-ui}main{max-width:1400px;margin:auto;padding:32px}h1{font-size:38px;letter-spacing:-1px;margin:12px 0}h2{margin-top:30px}p{line-height:1.6;color:#b8c8d5}a{color:#83dcc8}button,select,input{font:inherit;background:#243647;color:#e4edf5;border:1px solid #506477;padding:9px;border-radius:6px}input{min-width:250px}.eyebrow{color:#7ad8c3;letter-spacing:2px;font-size:12px}.warning{border-left:4px solid #e4b66a;background:#29303a;padding:14px}.cards{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin:24px 0}.card{background:#1c2a38;padding:20px;border-radius:8px}.card b{display:block;font-size:30px;color:#fff}.card span{color:#b4c2d1}.scroll{overflow:auto;max-height:600px}table{width:100%;border-collapse:collapse;font-size:13px}td,th{text-align:left;padding:12px;border-bottom:1px solid #344251}th{position:sticky;top:0;background:#1c2a38;white-space:nowrap}tr:hover{background:#1b2d3d}td.num{text-align:right;font-variant-numeric:tabular-nums}.toolbar{display:flex;gap:12px;flex-wrap:wrap;margin:16px 0}.plot{background:#1c2a38;padding:12px;border-radius:8px}svg{width:100%;height:auto}.small{font-size:12px}details{background:#182735;padding:16px;margin:8px 0}summary{cursor:pointer}pre{white-space:pre-wrap;line-height:1.6;color:#c5d7e5}@media(max-width:750px){main{padding:15px}.cards{grid-template-columns:repeat(2,1fr)}h1{font-size:29px}}</style></head><body><main>
<div class="eyebrow">LITERATURE · REPRODUCIBLE EXPERIMENTS · EVIDENCE</div><h1>ETF Signal Research Lab</h1>
<p>Fifty papers, a common evaluation framework, and an explicit distinction between published results and ETF adaptations.</p>
<div class="warning"><b>Exploratory research — no verified trading edge.</b> Fixed surviving ETF universe, revised public history, assumed opening execution and costs. Original-paper replications are blocked. Final 2024–2025 data remains sealed.</div>
<div class="cards" id="cards"></div>
<nav class="toolbar"><a href="papers.csv" download>Paper inventory CSV</a><a href="results/metrics.csv" download>All metrics CSV</a><a href="results/metrics.json" download>Detailed statistics JSON</a><a href="../SIGNAL_RESEARCH_HANDOFF.txt">Research handoff</a><a href="../SIGNAL_SIMILARITIES.txt">Signal similarities</a><a href="protocol.json">Frozen protocol</a><a href="data/manifest.json">Data provenance</a></nav>
<h2>Comparable ETF adaptations</h2><p>All rows use the same dates and constraints within each period. Base holds five sessions. Raw active return is relative to 90%-invested equal-weight buy-and-hold, not risk-adjusted alpha. Corrected p-values include all 231 variants and a conservative 50-paper floor.</p>
<div class="toolbar"><label>Period <select id="period"><option value="walk_forward">2021–2023 walk-forward</option><option value="validation">2019–2020 common validation</option></select></label><label>Variant <select id="variant"></select></label><label>Sort <select id="sort"><option value="signal">Signal ID</option><option value="net_cagr">Net CAGR</option><option value="sharpe_zero_cash_rate">Sharpe</option><option value="active_mean_annualized">Active mean</option></select></label></div>
<div class="scroll"><table><thead><tr><th>Signal</th><th>Net CAGR</th><th>Gross total</th><th>Volatility</th><th>Sharpe</th><th>Drawdown</th><th>Exposure</th><th>Active mean/year</th><th>Corrected p</th><th>Round trips</th></tr></thead><tbody id="metrics"></tbody></table></div>
<h2>Base equity curve</h2><div class="toolbar"><label>Signal <select id="chartSignal"></select></label></div><div class="plot"><svg id="chart" viewBox="0 0 1000 280" role="img" aria-label="Base strategy normalized equity curve"></svg></div><p id="detail" class="small"></p>
<details><summary>Statistical and execution conventions</summary><p>2,000 stationary-bootstrap samples, shared time indices across all strategies; block lengths 10, 20 and 40 sessions. Centered null and maximum studentized mean control the tested variant family. This estimates uncertainty for fixed strategies; it does not refit a model or create unseen regimes. Signal at prior close, entry at next adjusted open, complete nonoverlapping cohorts, 10-session split gap, risk ceiling 10% annual, gross cap90%, asset cap20%, zero cash yield. Base costs5bps/side. Adjusted prices approximate reinvested distributions; they are not a historical share/cash ledger. Daily bars do not establish obtainable opening fills.</p></details>
<h2>50-paper evidence inventory</h2><div class="toolbar"><input id="search" aria-label="Search papers" placeholder="Search title, author, family or ID"><label><input id="full" type="checkbox" style="min-width:0"> Downloaded full text only</label></div><p id="paperCount"></p><div id="papers"></div>
<p class="small">Source access does not imply complete replication review. Sample dates not verified from inspected sections remain unknown. Shared mechanisms and correlated adaptations are not independent confirmations.</p></main>
<script>const D=__DATA__;const $=id=>document.getElementById(id);const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));const pct=x=>x==null?'—':(x*100).toFixed(2)+'%';
$('cards').innerHTML=[[D.counts.papers_found,'Verified paper records'],[D.counts.downloaded_full_texts,'Downloaded full texts'],[D.counts.distinct_adaptations,'ETF adaptations'],[D.counts.variant_experiments,'Variant experiments'],[D.counts.robust_successes,'Robust successes']].map(([n,l])=>`<div class="card"><b>${n}</b><span>${l}</span></div>`).join('');
$('variant').innerHTML=[...new Set(D.metrics.map(r=>r.variant))].map(x=>`<option>${x}</option>`).join('');$('chartSignal').innerHTML=D.findings.map(x=>`<option value="${x.signal}">${x.signal} · ${esc(x.name)}</option>`).join('');
function metrics(){let rows=D.metrics.filter(x=>x.period===$('period').value&&x.variant===$('variant').value);let key=$('sort').value;rows.sort((a,b)=>key==='signal'?a.signal.localeCompare(b.signal):(b[key]??-Infinity)-(a[key]??-Infinity));$('metrics').innerHTML=rows.map(r=>`<tr data-signal="${r.signal}"><td>${r.signal} · ${esc(D.findings.find(f=>f.signal===r.signal).name)}</td>${[pct(r.net_cagr),pct(r.gross_total_return),pct(r.volatility),r.sharpe_zero_cash_rate?.toFixed(2)??'—',pct(r.max_drawdown),pct(r.mean_exposure),pct(r.active_mean_annualized),r.bootstrap_block_20.p_conservative.toFixed(3),r.round_trips].map(v=>`<td class="num">${v}</td>`).join('')}</tr>`).join('');document.querySelectorAll('tr[data-signal]').forEach(row=>row.onclick=()=>{$('chartSignal').value=row.dataset.signal;chart()});chart()}
function chart(){const period=$('period').value,id=$('chartSignal').value,c=D.curves[period],ys=c.series[id];const lo=Math.min(1,...ys),hi=Math.max(1,...ys);let points=ys.map((v,i)=>`${60+i/(ys.length-1)*900},${230-(v-lo)/(hi-lo||1)*200}`).join(' ');$('chart').innerHTML=`<text x="8" y="30" fill="#bacbda">${hi.toFixed(2)}</text><text x="8" y="230" fill="#bacbda">${lo.toFixed(2)}</text><line x1="60" y1="230" x2="960" y2="230" stroke="#536575"/><polyline points="${points}" fill="none" stroke="#7ad8c3" stroke-width="2"/><text x="60" y="265" fill="#bacbda">${c.dates[0]}</text><text x="850" y="265" fill="#bacbda">${c.dates.at(-1)}</text>`;let r=D.metrics.find(x=>x.signal===id&&x.variant==='base'&&x.period===period);$('detail').textContent=r.adaptation+' | Original papers: '+r.papers.join(', ')+'. Base curve only; changing the variant table does not change this base plot.'}
function papers(){let q=$('search').value.toLowerCase();let list=D.papers.filter(r=>(!$('full').checked||r.full_text_access.full_text_accessible)&&[r.id,r.title,r.family,...r.authors].join(' ').toLowerCase().includes(q));$('paperCount').textContent=list.length+' records shown';$('papers').innerHTML=list.map(r=>`<details><summary>${r.id} · ${esc(r.title)} <span class="small">[${esc(r.family)}]</span></summary><p>${esc(r.authors.join(', '))} · ${esc(JSON.stringify(r.publication_date))} · ${esc(r.publication_status)}</p><p><a href="${esc(r.url)}" target="_blank" rel="noopener">Canonical source</a> · <a href="paper_records/${r.id}.txt">Research record</a>${r.full_text_access.full_text_accessible?` · <a href="fulltext/${r.id}.pdf">Local public PDF</a>`:''}</p><pre>${esc(['Review: '+r.review_depth,'Market/data: '+r.original_market_and_data,'Sample: '+r.original_sample_period,'Horizon: '+r.original_horizon,'Mechanism: '+r.signal_and_economic_rationale,'Reported evidence: '+r.reported_findings_and_limits,'Status: '+r.implementation_status,'Adaptations: '+r.adaptation_ids.join(', '),'Changes: '+r.adaptation_changes.join(' '),'Blocker: '+r.blocker].join('\n\n'))}</pre></details>`).join('')}
['period','variant','sort'].forEach(id=>$(id).onchange=metrics);$('chartSignal').onchange=chart;$('search').oninput=papers;$('full').onchange=papers;metrics();papers();</script></body></html>'''


if __name__=='__main__':
    main()
