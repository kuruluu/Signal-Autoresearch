"""Reproduce archived input extraction without executing pickle payloads."""
import hashlib
import io
import json
import pickletools
import zipfile
from urllib.request import urlopen
import numpy as np
import pandas as pd
from .catalog import RESEARCH

def main():
    p=RESEARCH/'replication_first/p24_inputs'
    manifest=json.loads((p/'manifest.json').read_text())
    raw=p/'author_daily_2021.pkl'
    if not raw.exists():raw.write_bytes(urlopen(manifest['url'],timeout=30).read())
    if hashlib.sha256(raw.read_bytes()).hexdigest()!=manifest['sha256']:raise ValueError('Author snapshot hash changed')
    # The pinned payload was inspected: three raw arrays, date / vwretd / rf.
    # pickletools only decodes opcodes; no pickle GLOBAL or REDUCE is executed.
    blocks=[a for o,a,_ in pickletools.genops(raw.read_bytes()) if isinstance(a,(bytes,bytearray)) and len(a)>10000]
    if len(blocks)!=3 or any(len(b)!=200368 for b in blocks):raise ValueError('Pinned layout differs')
    dates=pd.DatetimeIndex(np.frombuffer(blocks[0],dtype='<M8[ns]'))
    frame=pd.DataFrame({'vwretd':np.frombuffer(blocks[1],dtype='<f8'),'rf':np.frombuffer(blocks[2],dtype='<f8')},index=dates)
    if not dates.is_monotonic_increasing or not dates.is_unique or dates.max()>=pd.Timestamp('2024-01-01'):raise ValueError('Invalid dates')
    target=p/'author_daily_2021.csv'
    # pandas to_csv(path) uses platform newlines on this Windows workspace.
    if target.exists():
        old=pd.read_csv(target,index_col='date',parse_dates=True)
        np.testing.assert_allclose(old.to_numpy(),frame.to_numpy(),rtol=1e-12,atol=1e-15,equal_nan=True)
        if not old.index.equals(dates):raise ValueError('CSV date mismatch')
    else:frame.to_csv(target,index_label='date')
    for r in json.loads((p/'archive_access.json').read_text()):
        if r['status']!='retrieved':continue
        file=p/r['url'].rsplit('/',1)[-1]
        if not file.exists():file.write_bytes(urlopen(r['url'],timeout=30).read())
        if hashlib.sha256(file.read_bytes()).hexdigest()!=r['sha256']:raise ValueError('Archive hash changed')
        with zipfile.ZipFile(file) as z:
            text=z.read(z.namelist()[0]).decode('utf-8-sig')
        target=p/'monthly_archive.txt'
        if not target.exists():target.write_text(text,encoding='utf-8')
        elif [x.strip() for x in target.read_text().splitlines() if x.strip()]!=[x.strip() for x in text.splitlines() if x.strip()]:raise ValueError('Monthly extraction mismatch')
    print('Pinned author arrays and monthly archive verified; no unpickling or new observations')

if __name__=='__main__':main()
