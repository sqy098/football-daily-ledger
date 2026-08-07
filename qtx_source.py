#!/usr/bin/env python3
"""qtx (球天下体育) mobile data source for the daily football ledger workflow.

- schedule: GET https://m.live.qtx.com/schedule?date=YYYYMMDD
    -> matches of that Beijing day, with Asian handicap (让球) and total (大小球) odds.
- over:     GET https://m.live.qtx.com/over?date=YYYYMMDD
    -> finished/status matches of that Beijing day with final scores.

All times are converted to Asia/Shanghai. No third-party dependencies.
"""
from __future__ import annotations

import gzip
import html
import json
import os
import re
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Shanghai")
QTX_BASE = "https://m.live.qtx.com"
USER_AGENT = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"
)
STATUS_NAMES = {
    "0": "异常", "1": "未开赛", "2": "上半场", "3": "中场", "4": "下半场",
    "5": "加时赛", "6": "加时赛", "7": "点球", "8": "完场", "9": "推迟",
    "10": "中断", "11": "腰斩", "12": "取消", "13": "待定",
}
_ITEM_RE = re.compile(
    r'<li class="item" data-id="(\d+)" competition-id="(\d+)" data-status="(\d+)".*?</li>',
    re.S,
)


def http_get(url: str, timeout: float = 45.0) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": QTX_BASE + "/",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read()
        if response.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
        return raw.decode("utf-8", "replace")


def _smalls(block_text: str) -> list[str]:
    return [v.strip() for v in re.findall(r"<small[^>]*>([^<]*)</small>", block_text)]


def _text(block: str, pattern: str, default: str = "") -> str:
    match = re.search(pattern, block)
    if not match:
        return default
    return html.unescape(match.group(1)).strip()


def parse_items(page_text: str, date_str: str, strict: bool = True) -> list[dict]:
    matches: list[dict] = []
    for match in _ITEM_RE.finditer(page_text):
        block = match.group(0)
        mid = match.group(1)
        ts_match = re.search(r'value="(\d{10})" id="match_time_' + mid + r'"', block)
        if not ts_match:
            continue
        kickoff = datetime.fromtimestamp(int(ts_match.group(1)), tz=TZ)
        if strict and kickoff.strftime("%Y-%m-%d") != date_str:
            continue
        league, start_time = "", ""
        lg = re.search(r'<p class="color_gray">([^<]*)<span class="TStartTime">([^<]*)</span>', block)
        if lg:
            league, start_time = lg.group(1).strip(), lg.group(2).strip()
        asia_block = re.search(r'id="odds_asia_' + mid + r'">(.*?)</p>', block, re.S)
        bs_block = re.search(r'id="odds_bs_' + mid + r'">(.*?)</p>', block, re.S)
        fenxi = ""
        fh = re.search(r'fenxi/([A-Za-z0-9]+)\.html', block)
        if fh:
            fenxi = fh.group(1)
        matches.append(
            {
                "id": mid,
                "competition_id": match.group(2),
                "status_id": match.group(3),
                "status_name": STATUS_NAMES.get(match.group(3), match.group(3)),
                "kickoff": kickoff.strftime("%Y-%m-%d %H:%M"),
                "league": league,
                "start_time": start_time,
                "home": _text(block, r'id="right_name_' + mid + r'">\s*([^<]+?)\s*</span>'),
                "away": _text(block, r'id="left_name_' + mid + r'">\s*([^<]+?)\s*</span>'),
                "score": _text(block, r'<p class="bf ScoreAll">([^<]*)</p>'),
                "half": _text(block, r'<p class="small color_gray Half">([^<]*)</p>'),
                "asia": _smalls(asia_block.group(1)) if asia_block else [],
                "bs": _smalls(bs_block.group(1)) if bs_block else [],
                "fenxi_hash": fenxi,
            }
        )
    return matches


def fetch_schedule(date_str: str) -> list[dict]:
    url = f"{QTX_BASE}/schedule?date={date_str.replace('-', '')}"
    return parse_items(http_get(url), date_str)


def fetch_results(date_str: str) -> list[dict]:
    url = f"{QTX_BASE}/over?date={date_str.replace('-', '')}"
    return parse_items(http_get(url), date_str)


def _find_skill_dir() -> str:
    env = os.environ.get("FOOTBALL_SKILL_DIR")
    if env and os.path.isdir(env):
        return env
    root = Path.home() / ".codex" / "plugins" / "cache" / "personal" / "football-handicap-analysis-ledger"
    candidates = sorted(root.glob("*/skills/football-handicap-analysis-ledger")) if root.exists() else []
    for cand in candidates:
        if (cand / "assets" / "league_dictionary.json").exists():
            return str(cand)
    return ""


_LEAGUE_MAP: dict[str, str] | None = None


def load_league_map() -> dict[str, str]:
    global _LEAGUE_MAP
    if _LEAGUE_MAP is not None:
        return _LEAGUE_MAP
    mapping: dict[str, str] = {}
    skill = _find_skill_dir()
    if skill:
        for filename in ("league_dictionary.json", "league_dictionary.supplement.json"):
            path = Path(skill) / "assets" / filename
            if not path.exists():
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8-sig"))
            except (OSError, json.JSONDecodeError):
                continue
            for entry in data.get("entries") or []:
                canonical = entry.get("canonical_name")
                if not canonical:
                    continue
                names = set(entry.get("aliases") or [])
                names.update(entry.get("source_names") or [])
                names.update(entry.get("raw_names") or [])
                names.add(canonical)
                for name in names:
                    if name:
                        mapping[name] = canonical
    # Repo-local overlay maintained by the daily pipeline.
    supplement_path = repo_supplement_path()
    if supplement_path.exists():
        try:
            data = json.loads(supplement_path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            data = {}
        for entry in data.get("entries") or []:
            canonical = entry.get("canonical_name")
            if not canonical:
                continue
            names = set(entry.get("aliases") or [])
            names.update(entry.get("raw_names") or [])
            names.add(canonical)
            for name in names:
                if name:
                    mapping[name] = canonical
    _LEAGUE_MAP = mapping
    return mapping


def standardize_league(name: str) -> str:
    lookup = load_league_map()
    return lookup.get(name, name)

def fetch_results_robust(date_str: str, attempts: int = 3, timeout: float = 45.0) -> list[dict]:
    """Fetch finished matches covering ``date_str`` despite CDN staleness.

    The qtx mobile ``over`` page honors ?date= but a CDN layer sometimes
    serves a stale cached variant (often another day).  We therefore fetch
    several URL variants (with cache-busting nonces) and merge every item
    by qtx match id, keeping items whose kickoff falls on the target date.
    """
    import random
    date_compact = date_str.replace("-", "")
    urls = [f"{QTX_BASE}/over?date={date_compact}"]
    urls += [f"{QTX_BASE}/over?date={date_compact}&_={random.randint(10**8, 10**9)}"
             for _ in range(attempts)]
    urls.append(f"{QTX_BASE}/over")
    by_id: dict[str, dict] = {}
    order: list[str] = []
    for url in urls:
        try:
            items = parse_items(http_get(url, timeout=timeout), date_str, strict=False)
        except Exception:
            continue
        for item in items:
            mid = item.get("id")
            if not mid:
                continue
            # Prefer items that kick off on the target date.
            same_day = item["kickoff"][:10] == date_str
            old = by_id.get(mid)
            if old is None or (same_day and old["kickoff"][:10] != date_str):
                if mid not in by_id:
                    order.append(mid)
                by_id[mid] = item
    return [by_id[mid] for mid in order]


def repo_supplement_path() -> Path:
    """Mutable league-dictionary overlay stored inside this git repo."""
    return Path(__file__).resolve().parent / "dictionary" / "league_dictionary.supplement.json"


def load_repo_supplement() -> dict:
    path = repo_supplement_path()
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            pass
    return {"schema_version": "1.0.0", "updated_at": None, "entry_count": 0, "entries": []}


def save_repo_supplement(data: dict) -> None:
    path = repo_supplement_path()
    path.parent.mkdir(exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def audit_leagues(raw_names) -> dict:
    """Auto-register previously unseen raw league names into the repo overlay.

    Canonical is set to the raw name so the site can group consistently; the
    entry is flagged ??? for later manual curation.
    """
    from datetime import datetime
    mapping = load_league_map()
    supplement = load_repo_supplement()
    entries = supplement.setdefault("entries", [])
    known = set(mapping)
    for entry in entries:
        known.add(entry.get("canonical_name") or "")
        known.update(entry.get("aliases") or [])
        known.update(entry.get("raw_names") or [])
    added = []
    for name in sorted({n.strip() for n in raw_names if n and n.strip()}):
        if name in known:
            continue
        entries.append({
            "canonical_name": name,
            "aliases": [name],
            "raw_names": [name],
            "updated_at": datetime.now(TZ).isoformat(timespec="seconds"),
            "auto_added": True,
            "maintenance_statuses": ["自动登记-待复核"],
            "notes": ["每日流水线自动登记，标准名待人工复核"],
        })
        mapping[name] = name
        added.append(name)
    if added:
        supplement["entry_count"] = len(entries)
        supplement["updated_at"] = datetime.now(TZ).isoformat(timespec="seconds")
        save_repo_supplement(supplement)
    return {"added": added, "known_total": len(mapping), "entry_count": len(entries)}


