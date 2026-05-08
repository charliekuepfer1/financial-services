---
description: Real-time P&L for any window — today, week-to-date, month-to-date, season, or YYYY-MM.
argument-hint: [today | wtd | mtd | season | YYYY-MM] (default: today)
---

Run a real-time P&L. Window: $ARGUMENTS (default `today` if empty).

1. `python plugins/vertical-plugins/small-business/lib/ledger.py pl <window>`
2. Render PDF: `python plugins/vertical-plugins/small-business/lib/render.py <window>`
3. Reply with one line: window, net income, PDF path. Don't paginate the PDF in chat.
4. If the owner asked a follow-up question (e.g., "why is fuel up?"), pull the relevant detail with another `pl` or `per-job` query — no narrative until they ask.
