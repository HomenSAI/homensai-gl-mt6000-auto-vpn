"""Request cooperative stop for the current owned overnight producer only."""
import json,re
from pathlib import Path
from serial_clone import require_clone,json_command
require_clone()
start=json.loads(Path('/lab/protocol-soak-start.json').read_text())
assert re.fullmatch('/tmp/homensai-protocol-lab-night[a-z0-9]+',start['root'])
code="from pathlib import Path; import json; root=Path("+repr(start['root'])+"); assert Path('/tmp/HOMENSAI_VIRTUAL_LAB').is_file(); (root/'STOP').touch(); print('CLONE_JSON:'+json.dumps({'stop_requested':True,'root':str(root)}))"
print(json.dumps(json_command(code,20)))
