"""Bounded SIP collection for registered P40 contemporary tests, no orders."""
import argparse,gzip,hashlib,json,time
from datetime import datetime,timezone
from pathlib import Path
from paperlab.broker import Alpaca,ApiError

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'research/replication_first/p40_contemporary_002'


def validate_bounds(start,end):
    a=datetime.fromisoformat(start.replace('Z','+00:00'))
    b=datetime.fromisoformat(end.replace('Z','+00:00'))
    if not a.tzinfo or not b.tzinfo or not a<b or a.year<2016 or b>=datetime(2024,1,1,tzinfo=timezone.utc):
        raise ValueError('Only bounded2016-2023requestsallowed')


def register():
    OUT.mkdir(exist_ok=True)
    spec={'id':'P40_contemporary_002','registered_at':datetime.now(timezone.utc).isoformat(),
          'type':'Contemporarymechanismtest, NOT1993-2013originalpaperreplication',
          'primary_sources':['https://guofuzhou.github.io/zpublications.html','https://guofuzhou.github.io/Appendix_IntraDay.pdf'],
          'instrument':'SPY only','development':'2016-2020','chronological_test':'2021-2023; alreadyviewedmarketperiod,notindependentconfirmation',
          'feature':'Adjusted09:59minuteclose/previousregularsessionlastminuteclose-1; includesovernightreturn',
          'target':'Adjusted15:59minuteclose/15:30minuteopen-1; earlycloseandnonstandardopensessionsomitted',
          'implementation_limits':['Thesearefixedminute-barproxiesforboundaryprices; closingauctionexcluded,notexactTAQpaperprices.',
                                   'Useadjustmentall toavoidmechanicaldividend/splitovernightgaps; syntheticadjustedunitsnotexecutablefillprices.',
                                   'Anyfuturetradingtestmustseparatelymodelbidask/latency,costs,borrow,capitaland3drawdowntiers.'],
          'data_quality':'Noimputation; requireall390regularsessionminutebarsanduniquetimestamps; reportallmissingdays; at least95%completeeligiblefullsessionsrequired. Firstsessionwithoutpriorcloseexcluded.',
          'mechanism_gate':'PositiveOLSslope and95%stationarybootstrapCIstrictlyabove0atblocks5/20/60sessions (5000paths,seeds40005/40020/40060); pluspositive2021-2023recursiveOLSforecastMSEimprovementoverexpandinghistoricalmeanafterinitial2016-2020training. Noalternativefilters/assets/windows.',
          'estimation':'OLSconstantandonefirsthalf-hourfeature; initialtraining2016-2020,refitexpandingdailyusingonlycompletedpriorsessions; whole2016-2023slopeisdescriptive.',
          'sealed_policy':'No2024-2025marketobservations; requireexplicitendbefore2024forEVERYrequest.',
          'code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    with (OUT/'registration.json').open('x') as f:json.dump(spec,f,indent=2)


def fetch():
    spec=json.loads((OUT/'registration.json').read_text())
    assert hashlib.sha256(Path(__file__).read_bytes()).hexdigest()==spec['code_sha256']
    broker=Alpaca('sip');manifest=[]
    calendar=broker.calendar('2016-01-01','2023-12-31')
    (OUT/'calendar.json').write_text(json.dumps(calendar,indent=2))
    for year in range(2016,2024):
        target=OUT/f'SPY_{year}_sip_1min.json.gz'
        meta=OUT/f'SPY_{year}_manifest.json'
        if target.exists() or meta.exists():
            if not(target.exists() and meta.exists()):raise ValueError('Partialyearartifactrequiresinspection')
            record=json.loads(meta.read_text());assert hashlib.sha256(target.read_bytes()).hexdigest()==record['sha256'];manifest.append(record);continue
        start=f'{year}-01-01T00:00:00Z';end=f'{year}-12-31T23:59:59Z';validate_bounds(start,end)
        params={'start':start,'end':end,'timeframe':'1Min','feed':'sip','adjustment':'all','sort':'asc','limit':10000}
        rows=[];seen=set();pages=0
        while True:
            for attempt in range(4):
                try:page=broker.request('/v2/stocks/SPY/bars',params,data=True);break
                except ApiError as exc:
                    if exc.status!=429 or attempt==3:raise
                    time.sleep(5)
            batch=page.get('bars') or []
            for row in batch:
                stamp=datetime.fromisoformat(row['t'].replace('Z','+00:00'))
                if stamp.year!=year:raise ValueError('Providerreturnedoutofboundsobservation')
            rows.extend(batch);pages+=1;token=page.get('next_page_token')
            if not token:break
            if token in seen:raise ValueError('Repeatedpaginationtoken')
            seen.add(token);params['page_token']=token
        with gzip.open(target,'wt',encoding='utf-8') as f:json.dump(rows,f)
        record={'year':year,'rows':len(rows),'pages':pages,'feed':'sip','adjustment':'all','start':start,'end':end,'sha256':hashlib.sha256(target.read_bytes()).hexdigest()}
        meta.write_text(json.dumps(record,indent=2));manifest.append(record)
        print('Completedyear',year,'rows',len(rows),'pages',pages,flush=True)
    (OUT/'input_manifest.json').write_text(json.dumps(manifest,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['register','fetch']);{'register':register,'fetch':fetch}[p.parse_args().action]()
