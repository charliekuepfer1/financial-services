---
name: categorize-txn
description: Map a parsed line to the exact locked category in chart-of-accounts.json. Use after parse-sloppy-input and before staging any row.
---

# Categorize transaction

The chart of accounts is **locked**. New categories require an explicit unlock token from the owner. If a transaction does not fit, your only options are: pick the closest existing category and add a note, or ask the owner whether to unlock.

## Decision tree

### Revenue

1. Was it a service performed? → `service.<tier>.<level>` from the chart.
2. Tip? → `tip`.
3. Refund? → `refund` (store amount as **negative**).
4. Gift card sold (not redeemed yet)? → `giftcard.sold` (deferred revenue).
5. Package pre-pay (multi-service prepaid bundle)? → `package.prepay` (deferred revenue).
6. Mileage / travel surcharge billed to client? → `fee.mileage`.
7. Add-on (pet hair, headlight, engine bay, etc.)? → `addon.<kind>`.

### Expense

| If the cue is... | Pick |
|---|---|
| chemicals, polish, wax, soap, sealant, microfibre, pad, applicator | `cogs.chemicals` (or `cogs.consumables` for towels/pads/applicators) |
| polisher, vacuum, extractor, generator, pressure washer, accessory | `equipment.tools` |
| polisher repair, machine service | `equipment.maintenance` |
| gas, fuel, Petro, Esso, Shell, Costco gas | `vehicle.fuel` |
| van insurance, commercial auto policy | `vehicle.insurance` |
| oil change, tires, brakes, van repair | `vehicle.maintenance` |
| plates, sticker, registration | `vehicle.registration` |
| Wagepoint payroll run, employee paycheque | `payroll.wages` |
| owner salary draw via payroll | `payroll.owner_salary` |
| CRA source deductions, CPP/EI remit | `payroll.source_deductions` |
| WSIB premium | `payroll.wsib` |
| Square subscription / monthly fee | `software.square` |
| Wagepoint subscription | `software.wagepoint` |
| Wave subscription | `software.wave` |
| ManyChat subscription | `software.manychat` |
| Meta / Facebook / IG ad spend | `marketing.meta_ads` |
| ManyChat automation campaign cost | `marketing.manychat_automation` |
| business cards, signage, vehicle wrap | `marketing.print_signage` |
| Square processing fee deducted from deposit | `fees.square_processing` |
| bank monthly fee, NSF | `fees.bank` |
| loan / line of credit interest | `fees.loan_interest` |
| accountant invoice | `professional.accountant` |
| phone bill, internet, mobile data | `office.phone` |
| course, certification, coaching | `training.courses` |
| business liability premium | `insurance.business_liability` |
| HST remittance to CRA | `tax.hst_remit` |
| owner moves money to personal | `owner.draw` (equity, not expense — flag it for the owner's review) |

If nothing fits: `other.uncategorized` with a **required** note. Surface it in the confirmation table so the owner sees it before approving.

## Before staging

Validate against `chart-of-accounts.json`. The `ledger.py stage` command will reject unknown categories — treat the rejection as a real bug, not a typo to bash through.
