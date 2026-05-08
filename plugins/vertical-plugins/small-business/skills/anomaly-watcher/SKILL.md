---
name: anomaly-watcher
description: Run threshold checks on revenue pace, category spend caps, per-job margin, and cash position. Surface only fired alerts, never noise. Used at the end of every daily-close and on demand.
---

# Anomaly watcher

Three classes of alert. Each one fires on a concrete number — no vibes.

## 1. Revenue pace

- **Window:** trailing 7 days, rolling.
- **Target:** `fiscal_year_target_revenue / season_op_days` (default $150K / ~89 op days ≈ $1,685/day).
- **Trigger:** rolling 7-day actual is ≥ 25% below 7-day target.
- **Severity:** `med` for 25–40% off, `high` for >40% off.
- **Message:** `Last 7d revenue $X vs target $Y — off pace Z%`.

## 2. Category monthly cap

Hard $/month ceilings on volatile categories. Defaults from `chart-of-accounts.json`:

| Category | Cap (CAD/mo) |
|---|---|
| `cogs.chemicals` | 1,200 |
| `vehicle.fuel` | 900 |
| `marketing.meta_ads` | 600 |
| `software.other` | 200 |

Trigger: MTD net spend > cap. Severity: `med`. The owner can edit caps in `chart-of-accounts.json` → `alerts.category_monthly_caps_cad`.

## 3. Per-job margin floor

Trailing 30-day window. For every job with revenue, compare margin to the tier floor. Trigger when below. See `per-job-margin` skill for the formula.

## 4. Cash floor

If `cash_floor_cad > 0` and gross cash-in MTD < floor, fire `low cash` alert. Default 0 = disabled.

## Run

```bash
python lib/ledger.py anomalies
```

## Output discipline

- **Silent when clean.** If no alerts fire, the agent says "Books look clean" and stops.
- **No counts of healthy categories.** Don't list what's fine. Only what's wrong.
- **Severity prefix.** `[HIGH]` and `[MED]`. No emoji.
- **One line per alert.**

## When the owner asks "what's the deal?"

Don't repeat the alert. Explain the underlying number: which category, which days, which jobs. Pull the relevant slice with `ledger.py pl <window>` or `ledger.py per-job` and answer with data.
