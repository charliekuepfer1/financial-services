---
description: One-time setup — create the books directory, copy the chart of accounts, install the engine deps.
argument-hint: [optional path for books dir]
---

One-time bootstrap for the bookkeeping agent.

1. If `$ARGUMENTS` is set, export `PD_BOOKS_DIR=$ARGUMENTS`. Otherwise default to `~/.premier-detailing-books`.
2. Ensure `reportlab` is installed: `pip install --quiet reportlab`.
3. `python plugins/vertical-plugins/small-business/lib/ledger.py init`
4. Confirm to the owner: books dir, ledger path, HST status (`none` until they register), daily target.
5. Tell them: "Run /close-day at the end of each day. Run /pl-now any time. Run /set-hst when your CRA registration completes."

That's it.
