---
description: Flip the HST switch once CRA registration is live. Schema is HST-ready from day one — this just turns it on.
argument-hint: <regular|quick> [--number=...] [--cadence=quarterly|annual]
---

Activate HST handling.

1. Parse `$ARGUMENTS` for method (`regular` or `quick`), HST number, filing cadence.
2. Run: `python plugins/vertical-plugins/small-business/lib/ledger.py set-hst --registered=true --method=<method> [--number=...] [--cadence=...]`
3. Confirm the new state to the owner with the JSON returned.
4. Note that future transactions will compute HST automatically by category default rate (regular) or remit at the Quick Method flat rate. Past transactions are unchanged — they pre-date registration.

If the user is unsure between regular and quick: at $150K with a service-heavy cost stack, Quick Method (8.8% on HST-included revenue, no ITCs except capital) usually nets out ahead of Regular. They can ask their accountant — the schema flips either way in one command.
