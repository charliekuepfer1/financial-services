---
name: daily-close
description: Run the 3–5 minute end-of-day session — sloppy input → confirmation → write → PDF render → alerts surfaced. The orchestration skill for /close-day.
---

# Daily close

Three to five minutes. No scrolling. The owner just finished a long day in the truck.

## The loop

1. **Receive the brain-dump.** Use `parse-sloppy-input` to extract candidate rows.
2. **Categorize.** Use `categorize-txn` to assign each row to a locked chart-of-accounts category.
3. **Mint job IDs** for new revenue lines: `python lib/ledger.py jobid` per new job.
4. **Stage every row** with `python lib/ledger.py stage <type> <amount> <category> --key=val ...`.
5. **Ask only on real ambiguity.** Batch all clarifying questions into **one message**. Do not drip-ask. If everything is clear, skip this step entirely.
6. **Show the confirmation table.** Compact, plaintext, single screen — see template below.
7. **On owner OK** → `python lib/ledger.py confirm all`. On targeted edits → `confirm <id>` per row, restage corrections, re-confirm.
8. **Render PDF** → `python lib/render.py today`. Print the path.
9. **Run anomalies** → `python lib/ledger.py anomalies`. Surface only fired alerts; if none, say "Books look clean."
10. **End with the one-line P&L** for today: revenue / expense / net / cash.

## Confirmation table — exact format

```
TODAY'S BOOKS — 2026-05-08

REVENUE
  PD-2026-001  John Tundra      Exterior Deluxe       Square     $285.00
  PD-2026-002  Mike F150        Interior Basic        Square     $165.00
                                            Tip                   Cash       $35.00
                                                              ────────────
                                                              TOTAL  $485.00

EXPENSES
  Petro                          Vehicle fuel         (87 km)               $62.40
  PDS                            Chemicals            → PD-2026-001         $118.00
  Meta                           Marketing — Meta ads                       $240.00
                                                              ────────────
                                                              TOTAL  $420.40

KM TODAY: 87
NET (today): $64.60

Anything to fix? Reply 'yes' to confirm, or tell me which row to change.
```

## Hard rules

- **Never re-ask** something the owner said in their dump. If they wrote "PDS" you do not ask which supplier.
- **Never invent** a job, a customer, or a service tier. Ambiguity → ask.
- **Never write to the ledger before confirmation.** All inputs go to staging first; `confirm` is the only path to the ledger.
- **5-minute hard out.** If the session passes 5 minutes of back-and-forth, stage what you have and tell the owner: "Parking the rest in staging — resume tomorrow with /close-day continue." The unconfirmed staging rows persist.
- **One message per phase.** Owner dump → one clarification message (if any) → one confirmation table → one final summary. Four messages max for the entire close.
