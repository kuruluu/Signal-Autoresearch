"""Verify frozen experiment inputs without changing or downloading observations."""
import hashlib
import json
from .catalog import ROOT, RESEARCH

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def verify():
    checks=[]
    def check(path, expected, kind):
        checks.append({'path':str(path.relative_to(ROOT)),'kind':kind,
                       'expected':expected,'actual':sha(path) if path.exists() else None})
    registration=json.loads((RESEARCH/'results/registration.json').read_text())
    check(RESEARCH/'protocol.json',registration['protocol_sha256'],'protocol')
    for name,value in registration['code_sha256'].items():
        check(ROOT/'researchlab'/name,value,'registered code')
    manifest=json.loads((RESEARCH/'data/manifest.json').read_text())
    for symbol,record in manifest['assets'].items():
        for ext,key in [('json','raw_sha256'),('csv','csv_sha256')]:
            check(RESEARCH/'data'/f'{symbol}.{ext}',record[key],'market data')
    for r in json.loads((RESEARCH/'papers.json').read_text(encoding='utf-8')):
        check(ROOT/r['source_file'],r['source_sha256'],'bibliography')
    for r in json.loads((RESEARCH/'fulltext_access.json').read_text()):
        if r.get('full_text_accessible'):
            check(RESEARCH/'fulltext'/f"{r['id']}.pdf",r['pdf_sha256'],'PDF')
    failures=[r for r in checks if r['actual']!=r['expected']]
    out=RESEARCH/'expansion_001';out.mkdir(exist_ok=True)
    result={'checks':checks,'passed':not failures,'failure_count':len(failures),
            'scope':'Existing recorded hashes; not independent validation of provider truth',
            'baseline_results':{str(p.relative_to(ROOT)):sha(p) for p in sorted((RESEARCH/'results').glob('*')) if p.is_file()}}
    path=out/'integrity.json'
    if path.exists():
        old=json.loads(path.read_text())
        if old['baseline_results']!=result['baseline_results']:
            raise ValueError('Original result files changed since this continuation began')
    path.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(f'{len(checks)} checks; {len(failures)} failures; original result hashes recorded')
    if failures:
        raise ValueError(failures)
    return result

if __name__=='__main__': verify()
