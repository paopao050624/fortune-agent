# Fortune Agent v0.4.0

v0.4.0 brings the main-branch report export, transparent library retrieval, expanded Agent evaluation and conservative Ba Zi calibration work into downloadable packages. It also supplies an eight-slide HTML project showcase with architecture, synthetic screenshots, a three-minute introduction and six-minute demo script.

## Changes

- Search 665 supplied source entries by question and module; show matching reasons, fixed provenance and missing books. Ba Zi and Zi Wei explanations retain mandatory anchors while selecting relevant context.
- Export reports as HTML, PNG or browser-printed PDF; preview source/private-field options. Known birth fields are hidden by default, but free text still requires review before sharing.
- Expand real-provider evaluation to 20 cases: original run meets stated checks in 19 cases; the failed I Ching case and corrected question reruns remain separate records. Enforce all selected I Ching passage IDs to avoid concise-answer prompt conflicts.
- Preserve existing Ba Zi numeric thresholds because there is no independent expert ground truth. Audit four threshold choices on six synthetic structural cases; withhold final balance selection when parameter scenarios disagree.
- Include `fortune-agent-showcase-v0.4.0.zip` alongside the wheel, source archive and checksums. Open `showcase/index.html` locally for keyboard navigation or printing. Screenshots contain synthetic data only.

## Install and verification

Python 3.10+ (3.11+ recommended); Node.js 18+ for bundled Zi Wei. Install `[all]` extras, run `fortune-doctor`, then `fortune-web --port 8766`. Version is checked across Python metadata, Node metadata, README, doctor and webpage footer. Full Python regression, browser flows, output-safety tests, container build and restart checks are in CI.

222 tests passed before release-metadata verification updates. The release workflow reruns full regression before producing packages. The source distribution includes documentation and showcase assets; the runtime wheel includes calculator catalogs and 78 original symbolic tarot cards.

## Honest limits

Ba Zi expert-label count is zero; calibration is structural/robustness auditing, not verified divination accuracy. Classical texts are limited, provenance-tracked excerpts, not complete paper collation. Western astrology remains ten geocentric tropical bodies with whole-sign houses. Cooperation-based cancellation cannot guarantee provider-side stop/refund. Local profiles are single-user plaintext records, not authenticated public accounts. No predictive-effectiveness claim is made.

v0.1, v0.2 and v0.3 release tags and assets are preserved as historical snapshots.
