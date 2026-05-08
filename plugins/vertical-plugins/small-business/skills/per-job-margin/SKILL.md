---
name: per-job-margin
description: Compute per-job profitability for a window — revenue minus chemicals, labor, travel, other — and flag jobs below the tier-specific margin floor. Use when the owner asks "which jobs are losing money" or before a season retrospective.
---

# Per-job margin

## Formula

```
margin% = (revenue_net − chemicals − labor − travel − other) / revenue_net
```

Where:
- **revenue_net** sums every `type=in` txn with the same `job_id`, net of HST.
- **chemicals** = sum of `cogs.chemicals` + `cogs.consumables` tagged to the job.
- **labor** = sum of `payroll.*` tagged to the job (employees) plus `owner_internal_rate_cad_per_hour × hours` for owner-worked jobs (when hours are tagged).
- **travel** = `vehicle.fuel` and `fee.mileage` tagged to the job.
- **other** = anything else tagged to the job (rare; usually equipment).

## Floors (from `chart-of-accounts.json` → `alerts.per_job_margin_floors`)

| Tier | Floor |
|---|---|
| Interior | 55% |
| Exterior | 50% |
| Premier (Full Detail Premier) | 50% |
| Ceramic | 60% |
| Correction | 55% |
| Maintenance | 45% |
| Default | 45% |

## Run

```bash
python lib/ledger.py per-job [--since=YYYY-MM-DD]
```

Default window: trailing 30 days.

## Surfacing

Sort ascending by margin. Bold any row where `below_floor: true`. Don't lecture — name the job, the actual margin, the floor, and the single biggest cost driver. Owner decides what to do.

## What "below floor" usually means

- **Chemicals too high** → wrong product applied, batch leak, or pricing too low for the work involved.
- **Travel too high** → far-out job that should have carried a `fee.mileage` charge to the customer.
- **Labor too high** → job took longer than scoped (re-clean, customer add-on done unbilled).

The skill computes; the owner judges.
