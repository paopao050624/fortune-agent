# Contributing

The package supports Python 3.10+; Python 3.11+ is recommended and CI tests 3.11/3.13. Install Node.js 18+, then run:

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

## Full browser and Docker acceptance

Use isolated synthetic profiles. Install Playwright 1.62.1 with `npm install --prefix work/browser-tools --no-save playwright@1.62.1`, then install Chromium with `node work/browser-tools/node_modules/playwright/cli.js install chromium` (Linux CI uses `--with-deps`).

```bash
docker build -t fortune-agent:validation .
docker run -d --name fortune-validation -p 127.0.0.1:18766:8766 -v fortune-validation-data:/app/work fortune-agent:validation fortune-web --bind 0.0.0.0 --port 8766 --external-port 18766 --cache /app/work/daily.sqlite3
python scripts/smoke_http.py http://127.0.0.1:18766
python scripts/verify_container.py prepare
docker restart fortune-validation
python scripts/smoke_http.py http://127.0.0.1:18766
python scripts/verify_container.py recover
FORTUNE_TEST_URL=http://127.0.0.1:18766 PLAYWRIGHT_MODULE_PATH=../work/browser-tools/node_modules/playwright node scripts/verify_web.cjs
python scripts/verify_container.py cleanup
docker stop fortune-validation
```

Provider-dependent UI responses are explicit browser stubs. This acceptance run does not bill the relay or verify live model availability. Screenshots and structured results are saved in `work/web-validation/screenshots`; do not run against a public/shared service or real profile data.
