"""Append completed research cycles and mirror the current handoff."""
import json
from datetime import datetime,timezone
from .catalog import RESEARCH,ROOT

def record(cycle,meaningful_progress,findings,evidence,next_step):
    path=RESEARCH/'replication_first'/'cycles.jsonl'
    if path.exists():
        existing=[json.loads(x) for x in path.read_text(encoding='utf-8').splitlines()]
        if any(r['cycle']==cycle for r in existing):
            raise ValueError('Cycle already recorded; append a new cycle ID')
    item={'cycle':cycle,'recorded_at_utc':datetime.now(timezone.utc).isoformat(),
          'meaningful_progress':meaningful_progress,'findings':findings,'evidence':evidence,
          'next_step':next_step,'continue':meaningful_progress}
    with path.open('a',encoding='utf-8') as f:f.write(json.dumps(item,ensure_ascii=False)+'\n')
    h=RESEARCH/'replication_first'/'HANDOFF.txt'
    with h.open('a',encoding='utf-8') as f:
        f.write(f'\nCYCLE {cycle} UPDATE\nMeaningful progress: {meaningful_progress}\n{findings}\nEvidence: '+', '.join(evidence)+f'\nNext step: {next_step}\n')
    (ROOT/'SIGNAL_RESEARCH_HANDOFF.txt').write_bytes(h.read_bytes())

