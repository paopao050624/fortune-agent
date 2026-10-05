"""Collect licenses for code actually bundled into the Node bridge."""
import json
from pathlib import Path

PACKAGES=['iztro','dayjs','i18next','lunar-lite','lunar-typescript','@babel/runtime']
parts=['Third-party notices for bundled Zi Wei runtime\n']
for name in PACKAGES:
    candidates=list(Path('node_modules/.pnpm').glob(name.replace('/','+')+'@*/node_modules/'+name+'/package.json'))
    if len(candidates)!=1:raise RuntimeError(f'Expected one installed version of {name}')
    metadata=json.loads(candidates[0].read_text())
    directory=candidates[0].parent
    licenses=[p for p in directory.iterdir() if p.name.lower() in ('license','license.md','license.txt','licence','licence.md')]
    if not licenses:raise RuntimeError(f'Missing license for {name}')
    parts.append(f"\n{name} {metadata['version']} ({metadata.get('license','see license')})\n")
    parts.append(licenses[0].read_text())
Path('src/fortune_agent/static/ziwei-notices.txt').write_text('\n'.join(parts))
