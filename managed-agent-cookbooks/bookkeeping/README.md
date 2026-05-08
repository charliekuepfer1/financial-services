# Bookkeeping Agent — managed-agent template

## Overview

End-of-day bookkeeping for owner-operated service businesses. Same source as the [`bookkeeping`](../../plugins/agent-plugins/bookkeeping) Cowork plugin — this directory is the Managed Agent cookbook for `POST /v1/agents`, used in **v2 autonomous mode**.

v1 = Cowork plugin, owner runs `/close-day` end of day, 3–5 minutes.
v2 = this cookbook, deployed headless, runs overnight against Square + bank feed + Wagepoint MCPs.

## Deploy

```bash
export ANTHROPIC_API_KEY=sk-ant-...
export SQUARE_MCP_URL=...
export BANK_MCP_URL=...
export WAGEPOINT_MCP_URL=...
../../scripts/deploy-managed-agent.sh bookkeeping
```

## Steering events

See [`steering-examples.json`](./steering-examples.json).

## Security & handoffs

Receipts and bank/payment-processor data are untrusted. Three-tier isolation:

| Tier | Touches untrusted docs? | Tools | Connectors |
|---|---|---|---|
| **`receipt-reader`** | **Yes** | `Read` only | None |
| Orchestrator | No | `Read`, `Bash`, `Glob`, `Grep`, `Agent` | Square, bank-feed, Wagepoint (read-only) |
| **`pdf-writer`** (Write-holder) | No | `Read`, `Write`, `Bash` | None |

`pdf-writer` produces `./out/books-<YYYY-MM-DD>.pdf`. Ledger writes happen via the orchestrator calling `lib/ledger.py` (which writes JSON to `$PD_BOOKS_DIR/ledger.json`).

## Confidence threshold for auto-confirm

The orchestrator auto-confirms staged rows where the parser's confidence ≥ 0.9. Below that, rows stay in staging and are flagged for the owner's morning review. Owner gets pinged only when:

- a HIGH-severity anomaly fires, or
- staging has > 5 unresolved rows.

## Handoff to v1

The owner's `/close-day` session sees auto-confirmed rows already in the ledger and any low-confidence rows still in staging. They review only the staging queue and the alerts.
