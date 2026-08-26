import re

with open("CHANGELOG.md", "r") as f:
    text = f.read()

header = "## [3.0.1] - 2026-08-25"

new_changes = """
### Added
- **Uber Eats Provider (Experimental)**
  - Hardened multi-provider integration (Schema v15).
  - Validated catalog capabilities for restaurants and supermarkets.
  - Upgraded parser for correct reference_price extraction via `purchasePriceV2`.
  - Confirmed UUID deduplication and observation history persistence safely alongside Rappi.
  - Finalized transport choice to `CDP_PRIMARY` (Android sandbox network inspection deemed unviable without root).
"""

text = text.replace(header, header + "\n" + new_changes)

with open("CHANGELOG.md", "w") as f:
    f.write(text)
