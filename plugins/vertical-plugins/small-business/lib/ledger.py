#!/usr/bin/env python3
"""
ledger.py — canonical ledger CRUD and queries for the bookkeeping agent.

Single JSON file as source of truth. PDF books are regenerated from it.
The agent calls this script via Bash. All commands print JSON on stdout
so the agent can parse without ambiguity.

Usage:
    ledger.py init                                  -- create books at $PD_BOOKS_DIR
    ledger.py add <type> <amount_cad> <category> [--key=val ...]
    ledger.py confirm <staging_id>                  -- promote staging row to ledger
    ledger.py stage <type> <amount_cad> <category> [--key=val ...]
    ledger.py today                                 -- todays totals + P&L
    ledger.py pl <window>                           -- window: today | wtd | mtd | season | YYYY-MM
    ledger.py per-job [--since=YYYY-MM-DD]          -- per-job profitability table
    ledger.py anomalies                             -- run threshold checks
    ledger.py jobid                                 -- mint next PD-YYYY-NNN
    ledger.py set-hst --registered=true --method=regular --number=...
    ledger.py path                                  -- print books dir

Env: PD_BOOKS_DIR (default ~/.premier-detailing-books)
"""
from __future__ import annotations
import json
import os
import sys
import shutil
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# ---------- locations ----------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[4]
COA_SOURCE = (
    Path(__file__).resolve().parents[1] / "data" / "chart-of-accounts.json"
)
BOOKS_DIR = Path(os.environ.get("PD_BOOKS_DIR", Path.home() / ".premier-detailing-books"))
LEDGER = BOOKS_DIR / "ledger.json"
COA = BOOKS_DIR / "chart-of-accounts.json"
RECEIPTS = BOOKS_DIR / "receipts"
PDFS = BOOKS_DIR / "pdf"
STAGING = BOOKS_DIR / "staging.json"


# ---------- helpers ------------------------------------------------------

def out(obj: Any) -> None:
    print(json.dumps(obj, indent=2, default=str))


def die(msg: str, code: int = 1) -> None:
    print(json.dumps({"error": msg}), file=sys.stderr)
    sys.exit(code)


def load(p: Path, default: Any = None) -> Any:
    if not p.exists():
        return default
    return json.loads(p.read_text())


def save(p: Path, obj: Any) -> None:
    p.write_text(json.dumps(obj, indent=2, default=str))


def parse_kv(args: list[str]) -> dict[str, str]:
    kv: dict[str, str] = {}
    for a in args:
        if a.startswith("--") and "=" in a:
            k, v = a[2:].split("=", 1)
            kv[k.replace("-", "_")] = v
    return kv


def today_str() -> str:
    return date.today().isoformat()


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


# ---------- init ---------------------------------------------------------

def cmd_init() -> None:
    BOOKS_DIR.mkdir(parents=True, exist_ok=True)
    RECEIPTS.mkdir(exist_ok=True)
    PDFS.mkdir(exist_ok=True)
    if not COA.exists():
        shutil.copy(COA_SOURCE, COA)
    if not LEDGER.exists():
        save(LEDGER, {
            "_meta": {
                "created": now_iso(),
                "schema_version": 1,
                "next_job_seq": {str(date.today().year): 1},
                "next_txn_seq": {today_str(): 1},
            },
            "transactions": [],
        })
    if not STAGING.exists():
        save(STAGING, {"rows": []})
    out({"ok": True, "books_dir": str(BOOKS_DIR), "ledger": str(LEDGER)})


def need_books() -> dict:
    if not LEDGER.exists():
        die("ledger not initialized — run: ledger.py init", 2)
    return load(LEDGER)


# ---------- ID minting ---------------------------------------------------

def mint_txn_id(book: dict) -> str:
    today = today_str()
    seq_map = book["_meta"].setdefault("next_txn_seq", {})
    n = seq_map.get(today, 1)
    seq_map[today] = n + 1
    return f"{today}-{n:03d}"


def mint_job_id(book: dict) -> str:
    yr = str(date.today().year)
    seq_map = book["_meta"].setdefault("next_job_seq", {})
    n = seq_map.get(yr, 1)
    seq_map[yr] = n + 1
    return f"PD-{yr}-{n:03d}"


def cmd_jobid() -> None:
    book = need_books()
    jid = mint_job_id(book)
    save(LEDGER, book)
    out({"job_id": jid})


# ---------- staging + confirm + add -------------------------------------

REQUIRED = {"in", "out"}


def build_row(kind: str, amount_cad: str, category: str, kv: dict[str, str], book: dict) -> dict:
    if kind not in REQUIRED:
        die(f"type must be 'in' or 'out', got {kind!r}")
    coa = load(COA)
    bucket = coa["revenue"] if kind == "in" else coa["expenses"]
    if category not in bucket:
        die(f"category {category!r} not in chart of accounts ({kind})")

    amount = round(float(amount_cad), 2)
    hst_method = coa["hst"]["method"]
    hst_amount = 0.0
    hst_rate = 0.0
    if hst_method != "none":
        if kind == "in":
            hst_rate = float(kv.get("hst_rate", coa["hst"]["province_default_rate"]))
            hst_amount = round(amount - amount / (1 + hst_rate), 2) if "hst_inclusive" in kv else round(amount * hst_rate, 2)
        else:
            default = bucket[category].get("default_hst_rate", 0)
            hst_rate = float(kv.get("hst_rate", default))
            hst_amount = round(amount - amount / (1 + hst_rate), 2) if hst_rate else 0.0

    row = {
        "id": mint_txn_id(book),
        "ts": now_iso(),
        "type": kind,
        "amount_cad": amount,
        "category": category,
        "supplier": kv.get("supplier"),
        "customer": kv.get("customer"),
        "job_id": kv.get("job_id"),
        "service_tier": bucket[category].get("tier"),
        "payment_method": kv.get("pay"),
        "note": kv.get("note"),
        "receipt": kv.get("receipt"),
        "km_today": float(kv["km"]) if "km" in kv else None,
        "hst": {"method": hst_method, "rate": hst_rate, "amount": hst_amount},
        "created_by": kv.get("by", "user"),
    }
    return row


def cmd_stage(argv: list[str]) -> None:
    if len(argv) < 3:
        die("usage: stage <in|out> <amount_cad> <category> [--key=val ...]")
    book = need_books()
    row = build_row(argv[0], argv[1], argv[2], parse_kv(argv[3:]), book)
    staging = load(STAGING, {"rows": []})
    staging["rows"].append(row)
    save(STAGING, staging)
    save(LEDGER, book)  # persist seq bumps
    out({"staged": row})


def cmd_confirm(argv: list[str]) -> None:
    book = need_books()
    staging = load(STAGING, {"rows": []})
    if not staging["rows"]:
        die("nothing staged")
    if argv and argv[0] != "all":
        keep = []
        promoted = []
        for r in staging["rows"]:
            if r["id"] == argv[0]:
                promoted.append(r)
            else:
                keep.append(r)
        staging["rows"] = keep
    else:
        promoted = staging["rows"]
        staging["rows"] = []
    book["transactions"].extend(promoted)
    save(LEDGER, book)
    save(STAGING, staging)
    out({"confirmed": [r["id"] for r in promoted]})


def cmd_add(argv: list[str]) -> None:
    if len(argv) < 3:
        die("usage: add <in|out> <amount_cad> <category> [--key=val ...]")
    book = need_books()
    row = build_row(argv[0], argv[1], argv[2], parse_kv(argv[3:]), book)
    book["transactions"].append(row)
    save(LEDGER, book)
    out({"added": row})


# ---------- queries ------------------------------------------------------

def in_window(ts: str, start: date, end: date) -> bool:
    d = datetime.fromisoformat(ts).date()
    return start <= d <= end


def window_dates(window: str) -> tuple[date, date]:
    today = date.today()
    if window == "today":
        return today, today
    if window == "wtd":
        return today - timedelta(days=today.weekday()), today
    if window == "mtd":
        return today.replace(day=1), today
    if window == "season":
        coa = load(COA)
        m, d = map(int, coa["_meta"]["season_start"].split("-"))
        start = date(today.year, m, d)
        m2, d2 = map(int, coa["_meta"]["season_end"].split("-"))
        end = date(today.year, m2, d2)
        return start, min(today, end)
    if len(window) == 7 and window[4] == "-":  # YYYY-MM
        y, m = map(int, window.split("-"))
        start = date(y, m, 1)
        end = (date(y, m + 1, 1) if m < 12 else date(y + 1, 1, 1)) - timedelta(days=1)
        return start, end
    die(f"unknown window {window!r}")
    return today, today  # unreachable


def pl_for(window: str) -> dict:
    book = need_books()
    coa = load(COA)
    start, end = window_dates(window)
    txns = [t for t in book["transactions"] if in_window(t["ts"], start, end)]

    revenue_by_tier: dict[str, float] = {}
    revenue_by_cat: dict[str, float] = {}
    expense_by_cat: dict[str, float] = {}
    hst_collected = 0.0
    hst_itc = 0.0
    cash_in = 0.0

    for t in txns:
        amt = t["amount_cad"]
        net = amt - t["hst"]["amount"] if t["hst"]["method"] != "none" else amt
        if t["type"] == "in":
            revenue_by_cat[t["category"]] = revenue_by_cat.get(t["category"], 0) + net
            tier = t.get("service_tier") or "other"
            revenue_by_tier[tier] = revenue_by_tier.get(tier, 0) + net
            hst_collected += t["hst"]["amount"]
            cash_in += amt
        else:
            expense_by_cat[t["category"]] = expense_by_cat.get(t["category"], 0) + net
            hst_itc += t["hst"]["amount"]

    revenue_total = sum(revenue_by_cat.values())
    expense_total = sum(expense_by_cat.values())
    target_pace = pace_target(coa, start, end)

    return {
        "window": window,
        "start": str(start),
        "end": str(end),
        "revenue_total_net": round(revenue_total, 2),
        "expense_total_net": round(expense_total, 2),
        "net_income": round(revenue_total - expense_total, 2),
        "revenue_by_tier": {k: round(v, 2) for k, v in revenue_by_tier.items()},
        "revenue_by_category": {k: round(v, 2) for k, v in revenue_by_cat.items()},
        "expense_by_category": {k: round(v, 2) for k, v in expense_by_cat.items()},
        "hst_collected": round(hst_collected, 2),
        "hst_itc": round(hst_itc, 2),
        "hst_owed_to_cra": round(hst_collected - hst_itc, 2),
        "cash_in_gross": round(cash_in, 2),
        "txn_count": len(txns),
        "vs_target_pace": target_pace,
    }


def pace_target(coa: dict, start: date, end: date) -> dict:
    annual = coa["_meta"]["fiscal_year_target_revenue"]
    season_m_start, season_d_start = map(int, coa["_meta"]["season_start"].split("-"))
    season_m_end, season_d_end = map(int, coa["_meta"]["season_end"].split("-"))
    yr = end.year
    s_start = date(yr, season_m_start, season_d_start)
    s_end = date(yr, season_m_end, season_d_end)
    season_days = (s_end - s_start).days + 1
    op_days_per_month = coa["_meta"]["operating_days_per_month"]
    season_op_days = (season_days / 30.0) * op_days_per_month
    daily_target = annual / season_op_days
    days_in_window = (end - start).days + 1
    return {
        "daily_target_cad": round(daily_target, 2),
        "window_target_cad": round(daily_target * days_in_window, 2),
        "season_op_days_est": round(season_op_days, 1),
    }


def cmd_pl(argv: list[str]) -> None:
    window = argv[0] if argv else "today"
    out(pl_for(window))


def cmd_today() -> None:
    out(pl_for("today"))


def cmd_per_job(argv: list[str]) -> None:
    book = need_books()
    coa = load(COA)
    kv = parse_kv(argv)
    since = date.fromisoformat(kv["since"]) if "since" in kv else date.today() - timedelta(days=30)

    jobs: dict[str, dict] = {}
    for t in book["transactions"]:
        if datetime.fromisoformat(t["ts"]).date() < since:
            continue
        jid = t.get("job_id")
        if not jid:
            continue
        j = jobs.setdefault(jid, {
            "job_id": jid, "revenue": 0.0, "chemicals": 0.0,
            "labor": 0.0, "travel": 0.0, "other": 0.0,
            "tier": None, "customer": None,
        })
        net = t["amount_cad"] - t["hst"]["amount"] if t["hst"]["method"] != "none" else t["amount_cad"]
        if t["type"] == "in":
            j["revenue"] += net
            j["tier"] = j["tier"] or t.get("service_tier")
            j["customer"] = j["customer"] or t.get("customer")
        else:
            cat = t["category"]
            if cat.startswith("cogs.chemicals") or cat.startswith("cogs.consumables"):
                j["chemicals"] += net
            elif cat == "vehicle.fuel" or cat == "fee.mileage":
                j["travel"] += net
            elif cat.startswith("payroll."):
                j["labor"] += net
            else:
                j["other"] += net

    floors = coa["alerts"]["per_job_margin_floors"]
    rows = []
    for j in jobs.values():
        cost = j["chemicals"] + j["labor"] + j["travel"] + j["other"]
        margin = (j["revenue"] - cost) / j["revenue"] if j["revenue"] else 0
        floor = floors.get(j["tier"] or "default", floors["default"])
        j["cost_total"] = round(cost, 2)
        j["margin_pct"] = round(margin, 4)
        j["margin_floor"] = floor
        j["below_floor"] = margin < floor
        for k in ("revenue", "chemicals", "labor", "travel", "other"):
            j[k] = round(j[k], 2)
        rows.append(j)
    rows.sort(key=lambda r: r["margin_pct"])
    out({"since": str(since), "jobs": rows})


# ---------- anomalies ----------------------------------------------------

def cmd_anomalies() -> None:
    book = need_books()
    coa = load(COA)
    today = date.today()
    alerts = []

    # revenue pace
    win_days = coa["alerts"]["revenue_pace_window_days"]
    pl_win = pl_for("today")
    daily_target = pl_win["vs_target_pace"]["daily_target_cad"]
    rolling_start = today - timedelta(days=win_days - 1)
    rolling = sum(
        (t["amount_cad"] - t["hst"]["amount"] if t["hst"]["method"] != "none" else t["amount_cad"])
        for t in book["transactions"]
        if t["type"] == "in" and in_window(t["ts"], rolling_start, today)
    )
    rolling_target = daily_target * win_days
    if rolling_target > 0:
        deficit = (rolling_target - rolling) / rolling_target
        if deficit >= coa["alerts"]["revenue_pace_alert_pct"]:
            alerts.append({
                "kind": "revenue_pace",
                "severity": "high" if deficit >= 0.4 else "med",
                "msg": f"Last {win_days}d revenue ${rolling:,.0f} vs target ${rolling_target:,.0f} — off pace {deficit:.0%}",
            })

    # category caps (MTD)
    mtd = pl_for("mtd")
    for cat, cap in coa["alerts"]["category_monthly_caps_cad"].items():
        spent = mtd["expense_by_category"].get(cat, 0)
        if spent > cap:
            alerts.append({
                "kind": "category_cap",
                "severity": "med",
                "msg": f"{cat} MTD ${spent:,.0f} exceeds cap ${cap:,.0f}",
            })

    # per-job margin floor (last 30d)
    pj_argv: list[str] = []
    book2 = need_books()
    coa2 = load(COA)
    since = today - timedelta(days=30)
    job_alerts: list[dict] = []
    jobs: dict[str, dict] = {}
    for t in book2["transactions"]:
        if datetime.fromisoformat(t["ts"]).date() < since:
            continue
        jid = t.get("job_id")
        if not jid:
            continue
        j = jobs.setdefault(jid, {"revenue": 0.0, "cost": 0.0, "tier": None})
        net = t["amount_cad"] - t["hst"]["amount"] if t["hst"]["method"] != "none" else t["amount_cad"]
        if t["type"] == "in":
            j["revenue"] += net
            j["tier"] = j["tier"] or t.get("service_tier")
        else:
            j["cost"] += net
    floors = coa2["alerts"]["per_job_margin_floors"]
    for jid, j in jobs.items():
        if not j["revenue"]:
            continue
        margin = (j["revenue"] - j["cost"]) / j["revenue"]
        floor = floors.get(j["tier"] or "default", floors["default"])
        if margin < floor:
            job_alerts.append({
                "kind": "job_margin",
                "severity": "med",
                "msg": f"Job {jid} margin {margin:.0%} below {j['tier'] or 'default'} floor {floor:.0%}",
            })
    alerts.extend(job_alerts)
    out({"alerts": alerts, "checked_at": now_iso()})


# ---------- HST switch ---------------------------------------------------

def cmd_set_hst(argv: list[str]) -> None:
    coa = load(COA)
    kv = parse_kv(argv)
    if "registered" in kv:
        coa["hst"]["registered"] = kv["registered"].lower() == "true"
    if "method" in kv:
        if kv["method"] not in ("none", "regular", "quick"):
            die("method must be one of: none | regular | quick")
        coa["hst"]["method"] = kv["method"]
    if "number" in kv:
        coa["hst"]["number"] = kv["number"]
    if "cadence" in kv:
        coa["hst"]["filing_cadence"] = kv["cadence"]
    save(COA, coa)
    out({"hst": coa["hst"]})


# ---------- dispatch -----------------------------------------------------

def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    cmd, *rest = sys.argv[1:]
    table = {
        "init": lambda: cmd_init(),
        "add": lambda: cmd_add(rest),
        "stage": lambda: cmd_stage(rest),
        "confirm": lambda: cmd_confirm(rest),
        "today": lambda: cmd_today(),
        "pl": lambda: cmd_pl(rest),
        "per-job": lambda: cmd_per_job(rest),
        "anomalies": lambda: cmd_anomalies(),
        "jobid": lambda: cmd_jobid(),
        "set-hst": lambda: cmd_set_hst(rest),
        "path": lambda: out({"books_dir": str(BOOKS_DIR), "ledger": str(LEDGER)}),
    }
    fn = table.get(cmd)
    if not fn:
        die(f"unknown command {cmd!r}. see {Path(__file__).name} --help-style header")
    fn()


if __name__ == "__main__":
    main()
