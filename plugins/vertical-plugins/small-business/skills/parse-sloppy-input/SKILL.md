---
name: parse-sloppy-input
description: Parse a single end-of-day brain-dump from the owner — mixed positive/negative amounts, supplier abbreviations, photo references, daily km — into structured staging rows. Use at the start of every /close-day session.
---

# Parse sloppy input

The owner types one message after a long day. They will not be tidy. Your job is to extract every dollar in and every dollar out, ask **only** about genuine ambiguity, and never re-ask anything they already said.

## What the owner will throw at you

```
+450 square john's tundra full detail, +180 square mike's f150 interior,
-60 fuel petro, -120 chemicals from PDS [photo], +35 tip cash,
drove 87km today, -240 manychat
```

## How to extract

| Pattern | Maps to |
|---|---|
| `+<amt>` or `<amt>` near a service word | revenue txn, type=`in` |
| `-<amt>` or expense words | expense txn, type=`out` |
| `square`, `cash`, `etransfer`, `e-transfer` | `payment_method` |
| `tip` | category=`tip` |
| customer name + vehicle | populates `customer` and `note` |
| service words ("interior", "exterior", "ceramic", "premier", "full detail", "wash", "correction") | maps to `service_tier` then to specific revenue category |
| supplier names (PDS, Auto Obsessed, TOC, Canadian Tire/CT, Amazon, Wagepoint, Wave, ManyChat, Meta, Square) | `supplier` |
| `[photo]`, `(receipt attached)`, image filename | `receipt` field — confirm the file path with the owner once, not per row |
| `drove Nkm`, `Nkm today`, `87km` | set `km` on the **day's first transaction only** |

## Disambiguation rules — ask once, only when needed

- **Service tier is ambiguous** ("john's tundra full detail" could be `service.full.basic` or `.deluxe` or `service.full.premier`). Ask: "John's Tundra — basic, deluxe, or Premier?"
- **Supplier mixed cart** (Amazon, Costco, CT can be chemicals + equipment + office in one receipt). Ask: "PDS receipt — all chemicals, or split equipment too?"
- **Bare dollar amount with no category cue.** Ask once: "What's the $X for?"
- **Tip without a payment method.** Default to `cash` unless owner said `square`.

## Never ask about

- HST — derived from category and `chart-of-accounts.json` `hst.method`. If `method = "none"`, store $0 and move on.
- Job ID — mint with `ledger.py jobid` for each new revenue line. The owner does not see job IDs.
- Internal hourly rate — pulled from the chart of accounts.

## Output

Stage every row with `ledger.py stage <type> <amount> <category> --key=val ...`. Do not call `add` or `confirm` until the owner approves the confirmation table from the `daily-close` skill.
