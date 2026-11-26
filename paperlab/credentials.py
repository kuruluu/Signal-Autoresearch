"""Load only Alpaca credentials from the project's ignored local .env file."""
import os
from pathlib import Path

NAMES=('APCA_API_KEY_ID','APCA_API_SECRET_KEY')
DEFAULT_FILE=Path(__file__).resolve().parents[1]/'.env'


def read_credentials(path=None,environ=None):
    environment=os.environ if environ is None else environ
    file=DEFAULT_FILE if path is None else Path(path)
    local={}
    if file.is_file():
        for line in file.read_text(encoding='utf-8-sig').splitlines():
            line=line.strip()
            if not line or line.startswith('#') or '=' not in line:continue
            name,value=line.split('=',1);name=name.strip();value=value.strip()
            if name not in NAMES:continue
            if len(value)>=2 and value[0]==value[-1] and value[0] in ('"',"'"):
                value=value[1:-1]
            local[name]=value
    # No eval, shell expansion, arbitrary environment mutation or secret logging.
    return {name:environment.get(name) or local.get(name) for name in NAMES}
