"""Publish only explicitly selected code, registrations and aggregate findings."""
import argparse,json,subprocess
from pathlib import Path
from paperlab.credentials import read_credentials

ROOT=Path(__file__).resolve().parents[1]
ROOT_FILES={'.gitignore','README.md','SIGNAL_RESEARCH_HANDOFF.txt','SIGNAL_SIMILARITIES.txt',
            'config.json','pyproject.toml','research.ps1','run.ps1'}
RESEARCH_FILES={'research/README.md','research/observed_periods.json','research/protocol.json'}
OWN_RECORDS={'registration.json','results.json','result.json','completion.json','INTERPRETATION.txt',
             'DISPOSITION.txt','AUDIT.txt','METHOD_AUDIT.txt','TARGETS.txt','PREDICTOR_AUDIT.txt',
             'ABORTED_INPUT_CHECK.txt','CONTROL_TIMING.txt','ACCESS_AUDIT.txt','INPUT_RECOVERY.txt',
             'RETURN_INPUT_AUDIT.txt','ERRATA.txt','analysis_freeze.json','quality_summary.json',
             'registration_addendum.json'}


def allowed(path):
    rel=path.relative_to(ROOT).as_posix()
    if rel in ROOT_FILES or rel in RESEARCH_FILES:return True
    if rel.startswith(('paperlab/','researchlab/','tests/')):
        return path.suffix=='.py' and '__pycache__' not in path.parts
    if rel.startswith('research/replication_first/'):
        if path.parent==ROOT/'research/replication_first':
            return path.suffix in ('.txt','.md','.json','.jsonl')
        return path.name in OWN_RECORDS
    return False


def selected():
    files=sorted(p for p in ROOT.rglob('*') if p.is_file() and allowed(p))
    # Match real locally configured secrets without ever printing their values.
    secrets=[s.encode() for s in read_credentials().values() if s and len(s)>=8]
    for path in files:
        raw=path.read_bytes()
        if any(secret in raw for secret in secrets):
            raise ValueError('Credential detected in selected checkpoint file: '+str(path.relative_to(ROOT)))
    return files


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--commit',action='store_true')
    parser.add_argument('--push',action='store_true');parser.add_argument('--message',default='Record notable research progress')
    args=parser.parse_args();files=selected()
    print(json.dumps({'selected_files':len(files),'excluded':'Credentials, raw market observations, third-party papers/text, account logs, binaries and downloaded archives'},indent=2))
    if not args.commit:return
    subprocess.run(['git','add','--',*[str(p.relative_to(ROOT)) for p in files]],cwd=ROOT,check=True)
    staged=subprocess.check_output(['git','diff','--cached','--name-only','-z'],cwd=ROOT).decode().split('\0')
    if any(not allowed(ROOT/p) for p in staged if p):raise ValueError('Unapproved staged file; inspect index before committing')
    changed=subprocess.run(['git','diff','--cached','--quiet'],cwd=ROOT).returncode
    if changed:subprocess.run(['git','commit','-m',args.message],cwd=ROOT,check=True)
    else:print('No checkpoint changes.')
    if args.push:
        remote=subprocess.check_output(['git','remote','get-url','origin'],cwd=ROOT).decode().strip()
        if remote not in ('https://github.com/kuruluu/Signal-Autoresearch.git','git@github.com:kuruluu/Signal-Autoresearch.git'):
            raise ValueError('Expected authorized kuruluu/Signal-Autoresearch remote')
        subprocess.run(['git','push','-u','origin','HEAD'],cwd=ROOT,check=True)


if __name__=='__main__':main()
