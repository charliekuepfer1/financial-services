---
name: render-pdf-ledger
description: Regenerate the PDF books for a window — daily, week-to-date, month-to-date, season, or a specific YYYY-MM. The PDF is the artifact the owner files; the JSON ledger is the engine.
---

# Render PDF ledger

The owner said: "books live as a PDF on the computer." The JSON ledger is the queryable source of truth; this skill produces the human-readable artifact every time something changes.

## Run

```bash
python lib/render.py <window>
```

Windows: `today` · `wtd` · `mtd` · `season` · `YYYY-MM`.

Output: `$PD_BOOKS_DIR/pdf/books-<window>-<today>.pdf` (path is printed on stdout as JSON).

## What's on the page

Single landscape sheet. Top to bottom:

1. **Header** — business name, window, generation timestamp, HST method.
2. **Headline strip** — six big numbers: revenue (net), expenses (net), net income, HST owed to CRA, window target, cash in (gross).
3. **Revenue by tier** + **Expenses by category** — side-by-side tables, sorted descending by dollar value.
4. **Per-job profitability** — every job in the window, lowest margin first, with the floor in the rightmost column. Below-floor margins are bold red.
5. **Alerts** — fired anomalies. Empty box says "No alerts. Books look clean." in green.

## When to render

- End of every `/close-day` session — render `today`.
- Owner runs `/pl-now` — render the requested window.
- End of every week (Sunday night) — render `wtd`.
- End of every month — render `mtd` for the just-closed month, named `YYYY-MM`.
- End of season — render `season`.

## What the agent says when handing over the PDF

One line. Path + the headline number. Example:

```
Books — today: net $64.60. PDF → /Users/owner/.premier-detailing-books/pdf/books-today-2026-05-08.pdf
```

Don't summarize the whole PDF in chat. The PDF is the summary.
