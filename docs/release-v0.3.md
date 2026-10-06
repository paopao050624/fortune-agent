# v0.3.0 历史发布记录（非当前版本）

> 本文仅记录旧版本，当前版本为 [v0.4.0](release-v0.4.md)。安装与使用以 [当前README](../README.md) 为准。

v0.3.0 packages the improvements made after v0.2.0: source-grounded Zi Wei interpretation, 78 original symbolic tarot SVG illustrations, an interactive astrology wheel with aspect filtering and SVG download, readable Markdown answers and compact calculation details, explicit profile consent, observed request stages, cooperative cancellation and stable retries, and question-focused response guidance.

## Install

Python 3.10+ (3.11+ recommended), Node.js 18+ for Zi Wei. Install the wheel with `[all]` extras or run `pip install -e '.[all]'` from the source archive. `fortune-doctor` and the webpage footer display the application version. Relay settings remain environment variables; no credentials are packaged.

## Validation and assets

207 Python tests passed including version metadata consistency; release CI reruns all tests and checks package version/tag alignment. Main-branch CI also verifies Docker builds, HTTP guards, restart persistence, desktop/mobile browser flows, formatted-output safety, profile consent and cancellation UI. Five real-provider evaluation cases passed their stated checks; samples remain limited and are not prediction-effectiveness evidence.

Release attachments include a wheel, source archive and SHA256 manifest. Bundled assets include 78 original symbolic SVG cards under MIT, fixed iztro runtime with dependency licenses, and 27 Zi Wei excerpts from fixed Wikisource revision 7913704 with attribution and transcription limits.

## Boundaries

Zi Wei excerpts are electronic text, not a complete paper-edition collation. Tarot illustrations are original symbols, not Waite/Smith artwork. Astrology remains tropical/geocentric/whole-sign with ten bodies. Ba Zi weights remain an explicit engineering approximation; the software does not claim a unified classical or empirically validated fortune algorithm.

Cancellation prevents later requests and adoption of delayed results; it does not guarantee the relay stops an already-sent request or refunds charges. Profiles are local single-user records, not authenticated public accounts. v0.2.0 tags and assets are unchanged.

Expanded evaluation, Ba Zi calibration work, report export and question-based library retrieval are follow-up work on main, not retroactive claims about this release snapshot.
