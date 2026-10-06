# v0.2.0 historical release

> Historical record. Current release: [v0.4.0](release-v0.4.md).

Added Zi Wei natal charts, tropical whole-sign Western astrology, multiple local profiles, chart coordinates and preferences, opt-in reading history, JSON archive restoration, visual tarot selection with stable reveals and followups, and additional spreads.

Python package includes the fixed iztro bridge and license notices; Node.js 18+ is required for Zi Wei. Install `.[all]` for model, calendar and astronomical dependencies. Run `fortune-doctor` to inspect local readiness without exposing credentials.

Source and wheel archives are prepared with a checksum manifest. Release attaches the current source and wheel archives. Do not include `.env`, credentials, personal databases, node_modules or temporary runtime files.

The implementation uses explicit calendar/house conventions. Zi Wei classical texts are not fully collated; Western astrology is limited to ten bodies and whole-sign houses. Profiles are local single-user records, not authenticated accounts. Docker publishes only to localhost.

Validation: 169 offline tests passed, JavaScript syntax and package checks passed. At the user's explicit request, final browser/full HTTP tests and Docker validation are skipped for this release. Docker configuration is supplied without a verified image build.

## Post-release validation and corrections

After the original v0.2.0 publication, full HTTP tests, 17 desktop/mobile browser groups, Docker builds and restart persistence were completed successfully. Main includes the external-port Host handling fix and profile-input clarification; the original v0.2.0 tag and downloadable archives are unchanged. See [follow-up verification](../evals/results/web-docker-review-2026-10-06.md) and [current README](../README.md) for main-branch behavior.
