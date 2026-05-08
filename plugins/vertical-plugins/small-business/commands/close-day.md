---
description: End-of-day bookkeeping session — sloppy input, confirmation, write, PDF. 3–5 min target.
argument-hint: [optional dump of today's in/out, or 'continue' to resume staging]
---

You are running `/close-day` for Premier Detailing.

The owner just hit you with $ARGUMENTS — or, if that's empty, ask once: "Drop today's in/out — sloppy is fine."

Run the **`daily-close`** skill end-to-end:

1. Parse the dump with `parse-sloppy-input`.
2. Categorize every row with `categorize-txn`.
3. Mint job IDs for new revenue lines.
4. Stage every row via `python plugins/vertical-plugins/small-business/lib/ledger.py stage ...`. (Use the absolute path or the path from this repo root.)
5. Ask the owner **one** consolidated clarification message — only if anything is genuinely ambiguous.
6. Show the confirmation table in the exact format from the `daily-close` skill.
7. On approval, `python lib/ledger.py confirm all`.
8. Render today's PDF: `python lib/render.py today`.
9. Run `python lib/ledger.py anomalies` and surface only fired alerts.
10. End with the one-line P&L for today.

Never re-ask anything the owner already said. Maximum four messages for the whole session.

If the user passed `continue`, skip parsing and load existing staging — show the confirmation table and proceed from step 6.
