import re

with open("AGENTS.md", "r") as f:
    text = f.read()

# Replace the Uber Eats experimental section text
old_text = "All Uber Eats logic must remain safely isolated in `src/dealhunter/providers/uber_eats/` and must not contaminate the V15 schema until data parity is 100% verified."
new_text = "All Uber Eats logic is safely isolated in `src/dealhunter/providers/uber_eats/` and has been **validated against the V15 multi-provider schema**, confirming proper UUID deduplication and observations history without contaminating Rappi data."

text = text.replace(old_text, new_text)

with open("AGENTS.md", "w") as f:
    f.write(text)
