DEALHUNTER_PHASE4K1_RELEASE_INTEGRITY

> [!IMPORTANT]
> Historical Phase 4 release-integrity snapshot. Its SHAs, schema and test
> counts describe that phase, not the current v3.2.0/schema v16 RC.

RC1
- tag SHA: b1afaa94c8ccda57b600b2c00ca8a4103b2fc2a6
- release exists: Yes
- CI run: 32769390355
- CI conclusion: success
- README contradiction: Yes (indicated v2.9.5, schema 9, 308 tests)
- release-report placeholders: Yes (`$(git rev-parse HEAD)`, `Pending Github Release`)
- changelog contradictions: Yes (duplicate v2.9.5 block, v2.9.4 as unreleased)
- tracked critical files: Yes (restored prior to merge, strictly tracked in RC1)

FIX
- files changed: README.md, CHANGELOG.md, docs/DEALHUNTER_V3_RC1_RELEASE.md, src/dealhunter/cli.py, src/dealhunter/web/templates/base.html, AGENTS.md
- functional changes: None (version bump only)
- docs-only changes: Yes
- provenance corrected: Yes

QUALITY
- collected: 393
- passed: 393
- failed: 0
- clean clone: Verified (CLI ok, Web app ok, fresh DB schema 14 ok, 0 FK errors)

RC2
- required: Yes
- reason: Contradictory information in RC1 README, shell placeholders in RC1 release report, and unorganized RC1 changelog.
- commit: 05397540ca931194d0925f9963c638b78ace41b2
- tag: v3.0.0-rc2
- CI run: 32771799961
- CI: success
- prerelease created: Yes (https://github.com/yorologo/DealHunter/releases/tag/v3.0.0-rc2)

DECISION
- RC1 preserved immutable: Yes
- documentation aligned: Yes
- provenance trustworthy: Yes
- release artifacts reproducible: Yes
- safe to begin Phase 5: Yes
