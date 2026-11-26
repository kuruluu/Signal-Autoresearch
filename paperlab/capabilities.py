"""Read-only Alpaca entitlement probes. Never submits orders or opens sealed dates."""
import json
from datetime import datetime, timezone
from pathlib import Path
from .broker import Alpaca, ApiError

PROBES = [
    ('paper_account', '/v2/account', None, False, None),
    ('exchange_calendar', '/v2/calendar', {'start':'2023-09-29','end':'2023-09-29'}, False, None),
    ('sip_daily_2016', '/v2/stocks/SPY/bars', {'start':'2016-01-04T00:00:00Z','end':'2016-01-05T00:00:00Z','timeframe':'1Day','feed':'sip','adjustment':'all','limit':2}, True, 'bars'),
    ('sip_minute_2023', '/v2/stocks/SPY/bars', {'start':'2023-09-29T14:00:00Z','end':'2023-09-29T14:01:00Z','timeframe':'1Min','feed':'sip','adjustment':'raw','limit':2}, True, 'bars'),
    ('sip_quotes_2023', '/v2/stocks/SPY/quotes', {'start':'2023-09-29T14:00:00Z','end':'2023-09-29T14:01:00Z','feed':'sip','limit':2}, True, 'quotes'),
    ('sip_trades_2023', '/v2/stocks/SPY/trades', {'start':'2023-09-29T14:00:00Z','end':'2023-09-29T14:01:00Z','feed':'sip','limit':2}, True, 'trades'),
]


def inspect(broker):
    results=[]
    for name,path,params,data,collection in PROBES:
        try:
            response=broker.request(path,params,data=data)
            if collection:
                count=len(response.get(collection) or [])
                detail={'rows':count,'status':'accessible_with_rows' if count else 'accessible_but_empty'}
            elif name=='paper_account':
                detail={'status':'accessible','account_status':response.get('status')}
            else:detail={'status':'accessible','rows':len(response)}
            results.append({'probe':name,**detail})
        except ApiError as exc:
            results.append({'probe':name,'status':'http_error','http_status':exc.status})
        except Exception as exc:
            # Never serialize arbitrary exceptions: provider messages may contain secrets.
            results.append({'probe':name,'status':'request_failed','error_type':type(exc).__name__})
    return results


def main():
    result={'checked_at':datetime.now(timezone.utc).isoformat(),'mode':'read_only_GET_probes',
            'date_policy':'Market observations requested only in2016and2023;2024-2025remainsealed',
            'scope':'Successful small probes verify those endpoints only, not complete history/universe quality.'}
    try:broker=Alpaca('iex')
    except ValueError:
        result.update(status='account_verification_blocked_missing_credentials',probes=[],
                      required_environment_variables=['APCA_API_KEY_ID','APCA_API_SECRET_KEY'])
    else:result.update(status='probes_completed',probes=inspect(broker))
    destination=Path('reports/alpaca_capabilities.json');destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
