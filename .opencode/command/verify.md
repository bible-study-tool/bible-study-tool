---
description: Run the full local verification (all gates CI runs) and summarize failures with remedies.
agent: build
---

Run the project's full local verification gate:

```bash
bash scripts/verify_all.sh
```

Then report to the user:
1. Each check and its pass/fail status (test suite, F1-F4 validators, source
   checksums).
2. For every failure: the exact error, which class it belongs to, and the
   remedy —
   - **Validator failure** (F1-F4): the entry and rule named in the message;
     fix the Markdown in materials/.
   - **Generated-artifact drift** (tripwire/checksum): never hand-edit;
     regenerate with the command printed in the failure, commit the artifact
     together with its updated data/PROVENANCE.md checksum.
   - **Ledger/corpus tripwire after a source re-pin**: this is the review
     gate — inspect the ledger/apparatus diff FIRST, review new
     disagreements, then regenerate and commit.
3. If everything passed, say so plainly and remind the user this is the same
   set of checks CI runs on their MR.

$ARGUMENTS
