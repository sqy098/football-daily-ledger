#!/usr/bin/env python3
"""Daily football ledger workflow - local JSON store + GitHub Pages.

Scans one Beijing day of football matches (schedule + market lines) into
``data/YYYY-MM-DD.json``, backfills settlement results the next day from the
qtx finished-match feed, and renders a self-contained GitHub Pages site
(``index.html``) from all stored days.

Commands:
  doctor                  Local readiness gate (store, source, git repo).
  scan  --date YYYY-MM-DD Freeze the day's schedule rows (idempotent).
  settle --date YYYY-MM-DD Backfill results for that day's rows (idempotent).
  rows  --date YYYY-MM-DD Print existing rows for that date.
  build                   Regenerate index.html from all stored days.
  open                    Open index.html in the default browser.
  daily [--date YYYY-MM-DD] Settle the previous day, then scan the given day.

Rules:
  - Matches without an opened line (handicap AND total both 未开盘) are skipped.
  - Rows are keyed by ``match_key`` = "{date}|{home}|{away}".
  - Settlement always uses the home side for handicap and over side for total.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Shanghai")

STATUS_FROZEN = "已冻结"
STATUS_IN_PROGRESS = "进行中"
STATUS_SETTLED = "已结算"
STATUS_PENDING = "待赛果"
NO_LINE = "未开盘"
SETTLE_WINDOW_DAYS = int(os.environ.get("FOOTBALL_SETTLE_WINDOW_DAYS", "5"))

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import qtx_source  # noqa: E402
from settle_markets import settle_handicap, settle_total  # noqa: E402

DATA_DIR = SCRIPT_DIR / "data"
SITE_FILE = SCRIPT_DIR / "index.html"
GIT_USER = os.environ.get("FOOTBALL_GIT_USER", "sqy098")
GIT_EMAIL = os.environ.get("FOOTBALL_GIT_EMAIL", "32825418+sqy098@users.noreply.github.com")


def log(message: str) -> None:
    print(message, flush=True)


def today_str() -> str:
    return datetime.now(TZ).strftime("%Y-%m-%d")


def data_path(date_str: str) -> Path:
    return DATA_DIR / f"{date_str}.json"


def load_day(date_str: str) -> dict:
    path = data_path(date_str)
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        data.setdefault("matches", [])
        return data
    return {"date": date_str, "updated_at": None, "matches": []}


def save_day(date_str: str, data: dict) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    data["date"] = date_str
    data["updated_at"] = datetime.now(TZ).isoformat(timespec="seconds")
    tmp = data_path(date_str).with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(data_path(date_str))


def build_handicap_pick(match: dict) -> str:
    asia = match.get("asia") or []
    if len(asia) >= 3 and asia[1] and asia[1] != "-":
        try:
            line = float(asia[1])
        except ValueError:
            return NO_LINE
        if line >= 0:
            return f"主让{line:g}（{asia[0]}/{asia[2]}）"
        return f"主受{-line:g}（{asia[0]}/{asia[2]}）"
    return NO_LINE


def build_ou_pick(match: dict) -> str:
    bs = match.get("bs") or []
    if len(bs) >= 3 and bs[1]:
        return f"大 {bs[1]}（{bs[0]}/{bs[2]}）"
    return NO_LINE


def build_optional(match: dict) -> str:
    parts = [f"qtx:{match['id']}", f"comp:{match['competition_id']}", f"status:{match['status_id']}"]
    if match.get("asia"):
        parts.append("asia:" + "/".join(match["asia"]))
    if match.get("bs"):
        parts.append("bs:" + "/".join(match["bs"]))
    if match.get("fenxi_hash"):
        parts.append("fenxi:" + match["fenxi_hash"])
    return ";".join(parts)


def parse_handicap_line(text: str | None) -> float | None:
    if not text or text == NO_LINE:
        return None
    match = re.match(r"主让([+-]?\d+(?:\.\d+)?)", text)
    if match:
        return float(match.group(1))
    match = re.match(r"主受([+-]?\d+(?:\.\d+)?)", text)
    if match:
        return -float(match.group(1))
    return None


def parse_total_line(text: str | None) -> float | None:
    if not text or text == NO_LINE:
        return None
    match = re.match(r"大\s*([+-]?\d+(?:\.\d+)?)", text)
    if match:
        return float(match.group(1))
    return None


def _is_water(value: str) -> bool:
    try:
        float(value)
        return True
    except ValueError:
        return False


def _parse_leagues(text: str | None) -> set[str] | None:
    if not text:
        return None
    return {item.strip() for item in text.split(",") if item.strip()}


# --------------------------------------------------------------------------
# scan
# --------------------------------------------------------------------------

def run_scan(date_str: str, dry_run: bool = False, min_water: float | None = None,
             leagues: set[str] | None = None) -> int:
    matches = qtx_source.fetch_schedule_robust(date_str)
    if not matches:
        log(f"scan {date_str}: no matches fetched from qtx")
        return 0
    audit = qtx_source.audit_leagues([m.get("league") or "" for m in matches])
    if audit["added"]:
        log(f"scan {date_str}: dictionary registered {len(audit['added'])} new leagues -> {', '.join(audit['added'][:10])}")
    if leagues:
        before = len(matches)
        matches = [m for m in matches
                   if qtx_source.standardize_league(m["league"]) in leagues or m["league"] in leagues]
        log(f"scan {date_str}: league filter kept {len(matches)}/{before}")
    if min_water is not None:
        before = len(matches)
        kept = []
        for m in matches:
            waters = [float(v) for v in (m.get("asia") or [])[:1] + (m.get("bs") or [])[:1] if _is_water(v)]
            if waters and min(waters) >= min_water:
                kept.append(m)
        matches = kept
        log(f"scan {date_str}: min-water {min_water} kept {len(matches)}/{before}")

    data = load_day(date_str)
    existing_keys = {m["match_key"] for m in data["matches"]}
    existing_ids = {str(m.get("qtx_id")) for m in data["matches"] if m.get("qtx_id")}

    written = skipped = no_line = 0
    now = datetime.now(TZ).isoformat(timespec="seconds")
    for match in matches:
        match_key = f"{date_str}|{match['home']}|{match['away']}"
        if match_key in existing_keys or str(match["id"]) in existing_ids:
            skipped += 1
            continue
        handicap_pick = build_handicap_pick(match)
        ou_pick = build_ou_pick(match)
        if handicap_pick == NO_LINE and ou_pick == NO_LINE:
            no_line += 1
            log(f"skip no-line {match_key} | {match['home']} vs {match['away']}")
            continue
        row = {
            "match_key": match_key,
            "qtx_id": match["id"],
            "competition_id": match["competition_id"],
            "kickoff": match["kickoff"],
            "league_raw": match["league"],
            "league": qtx_source.standardize_league(match["league"]),
            "home": match["home"],
            "away": match["away"],
            "status": STATUS_FROZEN,
            "handicap_pick": handicap_pick,
            "ou_pick": ou_pick,
            "optional": build_optional(match),
            "fenxi_hash": match.get("fenxi_hash") or "",
            "score": None,
            "half": None,
            "handicap_result": None,
            "ou_result": None,
            "note": None,
            "created_at": now,
            "updated_at": now,
        }
        if dry_run:
            log(f"[dry] would freeze {match_key} | {row['league']} | {row['handicap_pick']} | {row['ou_pick']}")
            written += 1
            continue
        data["matches"].append(row)
        written += 1
        log(f"frozen {match_key} | {row['league']} | {row['home']} vs {row['away']} | {row['handicap_pick']} | {row['ou_pick']}")
        time.sleep(0.1)
    if not dry_run:
        save_day(date_str, data)
    log(f"scan {date_str} done: written={written} skipped={skipped} no_line={no_line} total={len(matches)}")
    return written


# --------------------------------------------------------------------------
# settle
# --------------------------------------------------------------------------
def _kickoff_passed(kickoff_text: str | None) -> bool:
    if not kickoff_text:
        return True
    try:
        kickoff = datetime.strptime(kickoff_text, "%Y-%m-%d %H:%M").replace(tzinfo=TZ)
    except ValueError:
        return True
    return kickoff <= datetime.now(TZ)



def run_settle(date_str: str, dry_run: bool = False) -> tuple[int, int]:
    data = load_day(date_str)
    if not data["matches"]:
        log(f"settle {date_str}: no rows stored")
        return 0, 0
    results = qtx_source.fetch_results_robust(date_str)
    log(f"settle {date_str}: fetched {len(results)} result rows from qtx")
    by_id = {r.get("id"): r for r in results if r.get("id")}
    by_names: dict[tuple[str, str], dict] = {}
    for r in results:
        by_names.setdefault((r["home"], r["away"]), r)

    updated = pending = 0
    now = datetime.now(TZ).isoformat(timespec="seconds")
    for row in data["matches"]:
        record = None
        if row.get("qtx_id") and row["qtx_id"] in by_id:
            record = by_id[row["qtx_id"]]
        elif (row["home"], row["away"]) in by_names:
            record = by_names[(row["home"], row["away"])]
        if record is None:
            if row["status"] not in (STATUS_SETTLED, STATUS_PENDING) and _kickoff_passed(row.get("kickoff")):
                row["status"] = STATUS_PENDING
                row["note"] = "未查询到赛果（qtx 无记录）"
                row["updated_at"] = now
                pending += 1
            continue
        if record.get("status_id") != "8":
            if _kickoff_passed(row.get("kickoff")):
                row["status"] = STATUS_PENDING
                row["note"] = f"qtx状态={record.get('status_name')}，未结算"
                row["updated_at"] = now
                pending += 1
            continue
        score_match = re.match(r"^(\d+)-(\d+)$", (record.get("score") or "").strip())
        if not score_match:
            row["status"] = STATUS_PENDING
            row["note"] = f"qtx赛果异常 score={record.get('score')!r}"
            row["updated_at"] = now
            pending += 1
            continue
        home_goals, away_goals = int(score_match.group(1)), int(score_match.group(2))
        handicap_line = parse_handicap_line(row.get("handicap_pick"))
        total_line = parse_total_line(row.get("ou_pick"))
        payload = {
            "status": STATUS_SETTLED,
            "score": record.get("score"),
            "half": record.get("half"),
            "handicap_result": None,
            "ou_result": None,
            "note": f"比分 {record.get('score')}（半场 {record.get('half')}）来源qtx",
        }
        if handicap_line is not None:
            payload["handicap_result"] = settle_handicap("home", handicap_line, home_goals, away_goals)["result"]
        if total_line is not None:
            payload["ou_result"] = settle_total("over", total_line, home_goals, away_goals)["result"]
        if dry_run:
            log(f"[dry] would settle {row['match_key']} | {json.dumps(payload, ensure_ascii=False)}")
            updated += 1
            continue
        row.update(payload)
        row["updated_at"] = now
        updated += 1
        log(f"settled {row['match_key']} | {row['score']} | 让球={row['handicap_result'] or '-'} | 大小球={row['ou_result'] or '-'} | {row['note']}")
        time.sleep(0.1)
    if not dry_run:
        save_day(date_str, data)
    log(f"settle {date_str} done: settled={updated} pending={pending}")
    return updated, pending


# --------------------------------------------------------------------------
# rows / build / open / doctor / daily
# --------------------------------------------------------------------------

def run_rows(date_str: str) -> int:
    data = load_day(date_str)
    rows = sorted(data["matches"], key=lambda m: m.get("kickoff") or "")
    for row in rows:
        log(
            f"{row.get('qtx_id')} | {row['match_key']} | {row.get('league')} | "
            f"{row['home']} vs {row['away']} | {row.get('kickoff')} | "
            f"{row.get('handicap_pick')} | {row.get('ou_pick')} | {row.get('status')} | "
            f"让球={row.get('handicap_result') or '-'} | 大小球={row.get('ou_result') or '-'} | "
            f"比分={row.get('score') or '-'}"
        )
    log(f"rows {date_str}: {len(rows)}")
    return len(rows)


def run_build() -> int:
    import build_site
    build_site.generate_site(DATA_DIR, SITE_FILE)
    return 0


def run_open() -> int:
    if not SITE_FILE.exists():
        run_build()
    os.startfile(str(SITE_FILE))  # type: ignore[attr-defined]
    return 0


def run_dictionary() -> int:
    mapping = qtx_source.load_league_map()
    supplement = qtx_source.load_repo_supplement()
    entries = supplement.get("entries") or []
    pending = [e for e in entries if any("待复核" in s for s in (e.get("maintenance_statuses") or []))]
    log(json.dumps({
        "known_total": len(mapping),
        "repo_supplement_entries": len(entries),
        "pending_review": len(pending),
        "pending_samples": [e.get("canonical_name") for e in pending[:30]],
    }, ensure_ascii=False, indent=2))
    return 0


def run_settle_window(end_date: str, window_days: int = SETTLE_WINDOW_DAYS, dry_run: bool = False) -> None:
    """Settle the last ``window_days`` days, so a failed fetch one morning does
    not permanently miss settlement results."""
    end = datetime.strptime(end_date, "%Y-%m-%d").date()
    for i in range(window_days):
        day = (end - timedelta(days=i)).strftime("%Y-%m-%d")
        try:
            run_settle(day, dry_run=dry_run)
        except Exception as exc:
            log(f"settle {day}: ERROR {exc!r}")


def run_daily(date_str: str | None, dry_run: bool, min_water: float | None, leagues: set[str] | None) -> int:
    target = date_str or today_str()
    yesterday = (datetime.strptime(target, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
    log(f"=== daily run: settle window ending {yesterday} (last {SETTLE_WINDOW_DAYS} days) then scan {target} ===")
    run_settle_window(yesterday, dry_run=dry_run)
    run_scan(target, dry_run=dry_run, min_water=min_water, leagues=leagues)
    return 0


def run_doctor() -> int:
    report: dict = {"ok": True, "backend": "local-json+github-pages"}
    try:
        DATA_DIR.mkdir(exist_ok=True)
        probe = DATA_DIR / ".probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        report["store"] = {"ok": True, "dir": str(DATA_DIR)}
    except OSError as exc:
        report["store"] = {"ok": False, "error": str(exc)}
        report["ok"] = False
    try:
        page = qtx_source.http_get(f"{qtx_source.QTX_BASE}/over", timeout=30)
        report["source"] = {"ok": True, "bytes": len(page)}
    except Exception as exc:
        report["source"] = {"ok": False, "error": str(exc)}
        report["ok"] = False
    try:
        root = SCRIPT_DIR
        has_git = (root / ".git").is_dir()
        branch = ""
        if has_git:
            out = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=root,
                                 capture_output=True, text=True, timeout=15)
            branch = out.stdout.strip()
        report["git"] = {"ok": has_git, "branch": branch, "remote": _git_remote(root)}
        if not has_git:
            report["ok"] = False
    except Exception as exc:
        report["git"] = {"ok": False, "error": str(exc)}
        report["ok"] = False
    days = sorted(p.stem for p in DATA_DIR.glob("*.json")) if DATA_DIR.exists() else []
    report["stored_days"] = days
    log(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


def _git_remote(root: Path) -> str:
    try:
        out = subprocess.run(["git", "remote", "get-url", "origin"], cwd=root,
                             capture_output=True, text=True, timeout=15)
        return out.stdout.strip()
    except Exception:
        return ""


# --------------------------------------------------------------------------
# cli
# --------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("doctor").set_defaults(func=lambda a: run_doctor())
    sub.add_parser("dictionary").set_defaults(func=lambda a: run_dictionary())

    p_scan = sub.add_parser("scan")
    p_scan.add_argument("--date", default=None)
    p_scan.add_argument("--dry-run", action="store_true")
    p_scan.add_argument("--min-water", type=float, default=None)
    p_scan.add_argument("--leagues", default=None)
    p_scan.set_defaults(func=lambda a: run_scan(a.date or today_str(), a.dry_run, a.min_water, _parse_leagues(a.leagues)))

    p_settle = sub.add_parser("settle")
    p_settle.add_argument("--date", default=None)
    p_settle.add_argument("--dry-run", action="store_true")
    p_settle.set_defaults(func=lambda a: run_settle(a.date or today_str(), a.dry_run))

    p_rows = sub.add_parser("rows")
    p_rows.add_argument("--date", default=None)
    p_rows.set_defaults(func=lambda a: run_rows(a.date or today_str()))

    sub.add_parser("build").set_defaults(func=lambda a: run_build())
    sub.add_parser("open").set_defaults(func=lambda a: run_open())

    p_daily = sub.add_parser("daily")
    p_daily.add_argument("--date", default=None)
    p_daily.add_argument("--dry-run", action="store_true")
    p_daily.add_argument("--min-water", type=float, default=None)
    p_daily.add_argument("--leagues", default=None)
    p_daily.set_defaults(func=lambda a: run_daily(a.date, a.dry_run, a.min_water, _parse_leagues(a.leagues)))

    args = parser.parse_args()
    if args.func:
        args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())




