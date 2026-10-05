# Contributing

Install Python 3.11+ and Node.js 18+, then run:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[all]'
python -W error::ResourceWarning -m unittest discover -s tests -v
python -m pip install build
python -m build
```

The Zi Wei bridge is already bundled. To rebuild it, install pnpm and run `pnpm install --frozen-lockfile`, then `pnpm run build:ziwei`. Esbuild's optional platform binary must be installed; permit its install script when your package manager requires it. Rebuild the bundled notices with `python scripts/build_ziwei_notices.py` after dependency changes.

Keep API keys, personal profiles, databases, and real birth information out of commits. Use synthetic evaluation fixtures. Describe algorithm versions, timezone/calendar conventions, source provenance and missing conditions. Tests verify software behavior, not the predictive validity of divination.

Submit changes through a pull request with a short description and relevant validation. A new calculator should return reproducible facts before model interpretation, preserve its results on followups, and ask for missing inputs.
