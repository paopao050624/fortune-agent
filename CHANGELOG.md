# Changelog

## Unreleased

- Add three-coin I Ching casting, six user-supplied line totals, moving lines, and main/changed hexagrams in the CLI and local web interface.
- Preserve a source-linked lookup table for all 64 combinations and individual simulated coin records; no oracle-text interpretation is implemented yet.
- Accept user-supplied four pillars in the CLI and local web interface.
- Validate individual pillars against the sexagenary cycle and explicitly preserve unknown birth time, timezone, solar terms, and day-boundary conventions.
- Reuse source-linked interpretation and relationship calculations without inventing a birth date or claiming the supplied chart is calendar-verified.

## 0.1.0

First local prototype. This is a development release, not a complete implementation of all planned divination systems.

- Complete 78-card tarot deck, one-card and three-card spreads, automatic and selected draws.
- Relay-compatible Responses API interpretation with direct and gentle styles.
- Traceable Waite card meanings and fixed comparative evaluation cases.
- Daily tarot card by profile, local date, and timezone, with first-interpretation caching.
- Four pillars for China standard time, explicit day-boundary rules, calculated ten-god and hidden-stem relationships.
- Limited, source-linked excerpts from Di Tian Sui and Zi Ping Zhen Quan.
- Financial-pattern method checklist that keeps unresolved conditions explicit.
- Local browser interface for tarot, daily tarot, and four-pillar calculations.
- Offline tests, reproducible evaluation fixtures, and package build workflow.

Known limits: no complete strength, pattern, useful-god, or luck-cycle calculation; no Zi Wei Dou Shu, I Ching, or Western astrology; no public deployment or account system. Real evaluations are small, reviewed samples. The browser layout still requires visual acceptance in a supported browser environment.
