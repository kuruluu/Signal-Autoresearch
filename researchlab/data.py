"""Cached public observations, corporate-action payloads and exchange sessions."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
import numpy as np
import pandas as pd
from .catalog import ROOT, RESEARCH, get_json


def protocol():
    path = RESEARCH / 'protocol.json'
    return json.loads(path.read_text()), hashlib.sha256(path.read_bytes()).hexdigest()


def download():
    p, fingerprint = protocol()
    out = RESEARCH / 'data'
    out.mkdir(parents=True, exist_ok=True)
    manifest = {'provider': 'Yahoo Finance chart API; unofficial public research access',
                'protocol_sha256': fingerprint, 'assets': {}, 'sealed_final_downloaded': False}
    for symbol in p['universe']:
        params = {'period1': int(datetime.fromisoformat(p['data_start']).replace(tzinfo=timezone.utc).timestamp()),
                  'period2': int(datetime.fromisoformat(p['download_end_exclusive']).replace(tzinfo=timezone.utc).timestamp()),
                  'interval': '1d', 'events': 'div,splits'}
        url = f'https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?' + urlencode(params)
        raw_path = out / f'{symbol}.json'
        if not raw_path.exists():
            response = get_json(url)
            raw_path.write_text(json.dumps(response), encoding='utf-8')
        response = json.loads(raw_path.read_text(encoding='utf-8'))
        chart = response['chart']['result'][0]
        frame = normalize_chart(chart)
        if frame.index.max() >= pd.Timestamp(p['download_end_exclusive']):
            raise ValueError('Holdout guard: provider returned sealed-period bars')
        frame.to_csv(out / f'{symbol}.csv', index_label='date')
        manifest['assets'][symbol] = {'url': url, 'raw_sha256': hashlib.sha256(raw_path.read_bytes()).hexdigest(),
                                     'csv_sha256': hashlib.sha256((out / f'{symbol}.csv').read_bytes()).hexdigest(),
                                     'cached_file_mtime_utc': datetime.fromtimestamp(raw_path.stat().st_mtime, timezone.utc).isoformat(),
                                     'first': str(frame.index.min().date()), 'last': str(frame.index.max().date()),
                                     'rows': len(frame), 'dividend_events': len(chart.get('events', {}).get('dividends', {})),
                                     'split_events': len(chart.get('events', {}).get('splits', {}))}
        print('Cached', symbol, len(frame), flush=True)
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    return manifest


def normalize_chart(chart):
    dates = pd.to_datetime(chart['timestamp'], unit='s', utc=True).tz_convert('America/New_York').tz_localize(None).normalize()
    q = chart['indicators']['quote'][0]
    frame = pd.DataFrame({k: q[k] for k in ('open', 'high', 'low', 'close', 'volume')}, index=dates)
    frame['adj_close'] = chart['indicators']['adjclose'][0]['adjclose']
    if frame.index.duplicated().any() or not frame.index.is_monotonic_increasing:
        raise ValueError('Duplicate or unordered source dates')
    if not np.isfinite(frame.to_numpy()).all() or (frame <= 0).any().any():
        raise ValueError('Missing/nonpositive/nonfinite price or volume; no silent forward filling')
    tolerance = frame['high'] * 1e-6
    if ((frame['low'] - tolerance > frame[['open', 'close']].min(axis=1)) |
        (frame['high'] + tolerance < frame[['open', 'close']].max(axis=1))).any():
        raise ValueError('Inconsistent OHLC')
    # Adjusted units approximate reinvested distributions; not an actual cash dividend ledger.
    frame['adjustment_factor'] = frame.adj_close / frame.close
    frame['adj_open'] = frame.open * frame.adjustment_factor
    frame['dollar_volume'] = frame.close * frame.volume
    return frame


def load_panel():
    import exchange_calendars as xcals
    p, fingerprint = protocol()
    out = RESEARCH / 'data'
    manifest = json.loads((out / 'manifest.json').read_text())
    if manifest['protocol_sha256'] != fingerprint:
        raise ValueError('Protocol differs from data manifest; create a new registered experiment')
    frames = {}
    for symbol in p['universe']:
        file = out / f'{symbol}.csv'
        if hashlib.sha256(file.read_bytes()).hexdigest() != manifest['assets'][symbol]['csv_sha256']:
            raise ValueError('Cached data checksum mismatch: ' + symbol)
        frames[symbol] = pd.read_csv(file, index_col='date', parse_dates=True)
    start = max(f.index.min() for f in frames.values())
    end = min(f.index.max() for f in frames.values())
    cal = xcals.get_calendar('XNYS', start=p['data_start'], end=p['download_end_exclusive'])
    sessions = cal.sessions_in_range(start, end).tz_localize(None)
    for symbol, frame in frames.items():
        missing = sessions.difference(frame.index)
        extra = frame.loc[start:end].index.difference(sessions)
        if len(missing) or len(extra):
            raise ValueError(f'{symbol}: exchange calendar mismatch; missing={list(missing)}, extra={list(extra)}')
    if sessions.max() >= pd.Timestamp(p['sealed_final'][0]):
        raise ValueError('Sealed final data prohibited')
    panel = {key: pd.DataFrame({s: f.loc[sessions, key] for s, f in frames.items()})
             for key in ['adj_open', 'adj_close', 'close', 'volume', 'dollar_volume']}
    schedule = cal.schedule.loc[sessions]
    schedule.to_csv(out / 'exchange_schedule.csv', index_label='session')
    (out / 'quality.json').write_text(json.dumps({'common_first': str(start.date()), 'common_last': str(end.date()),
        'sessions': len(sessions), 'missing_sessions': 0, 'calendar': 'XNYS',
        'adjustment': 'adj_open = open * adj_close / close; approximate total-return units',
        'limitations': p['known_limits']}, indent=2))
    return panel, p


if __name__ == '__main__':
    download()
    panel, _ = load_panel()
    print('Validated', len(panel['adj_open']), 'common exchange sessions')
