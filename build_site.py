#!/usr/bin/env python3
"""Generate a self-contained GitHub Pages site from stored daily JSON files.

Reads data/YYYY-MM-DD.json and writes index.html with an embedded dataset,
a stats dashboard, filters, and per-match cards (all stored fields + P&L).
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Shanghai")

RESULT_PAYOUT = {
    "赢": 1.0,
    "赢半": 0.5,
    "走水": 0.0,
    "输半": -0.5,
    "输": -1.0,
}


def parse_home_odds(pick: str) -> float | None:
    import re
    if not pick:
        return None
    m = re.search(r"（([\d.]+)/", pick)
    return float(m.group(1)) if m else None


def parse_over_odds(pick: str) -> float | None:
    import re
    if not pick:
        return None
    m = re.search(r"（([\d.]+)/", pick)
    return float(m.group(1)) if m else None


def payout(result: str | None, odds: float | None) -> float | None:
    if not result or odds is None:
        return None
    base = RESULT_PAYOUT.get(result)
    if base is None:
        return None
    if base > 0:
        return round(base * odds, 3)
    return base


def generate_site(data_dir: Path, site_file: Path) -> None:
    days: dict[str, dict] = {}
    if data_dir.exists():
        for path in sorted(data_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if data.get("matches"):
                days[data["date"]] = data
    payload = {
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "days": days,
    }
    data_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    html = TEMPLATE.replace("__DATA_JSON__", data_json)
    site_file.write_text(html, encoding="utf-8")
    print(f"build: wrote {site_file} ({len(html)} bytes, {len(days)} days)")


TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>足球每日台账 · Asian Handicap Ledger</title>
<style>
:root{
  --bg:#0e1420; --panel:#171f2e; --panel2:#1d2739; --line:#2a3650;
  --text:#e8eef7; --muted:#93a3bd; --gold:#f5c451; --green:#4ade80;
  --red:#f87171; --blue:#60a5fa; --purple:#c084fc;
}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);font-family:"Segoe UI",system-ui,"Microsoft YaHei",sans-serif;line-height:1.45;padding:20px 16px 60px}
.wrap{max-width:1080px;margin:0 auto}
header h1{font-size:24px;font-weight:700;letter-spacing:.5px}
header .sub{color:var(--muted);font-size:13px;margin-top:4px}
.badge{display:inline-block;padding:2px 10px;border-radius:999px;font-size:12px;font-weight:600}
.b-freeze{background:rgba(96,165,250,.15);color:var(--blue);border:1px solid rgba(96,165,250,.4)}
.b-live{background:rgba(245,196,81,.15);color:var(--gold);border:1px solid rgba(245,196,81,.4)}
.b-pending{background:rgba(147,163,189,.12);color:var(--muted);border:1px solid rgba(147,163,189,.35)}
.b-done{background:rgba(74,222,128,.13);color:var(--green);border:1px solid rgba(74,222,128,.4)}
.b-win{background:rgba(74,222,128,.14);color:var(--green)}
.b-halfwin{background:rgba(74,222,128,.09);color:#86efac}
.b-push{background:rgba(147,163,189,.12);color:#cbd5e1}
.b-halfloss{background:rgba(248,113,113,.1);color:#fca5a5}
.b-loss{background:rgba(248,113,113,.16);color:var(--red)}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:18px 0}
.stat{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:12px 14px}
.stat .k{font-size:12px;color:var(--muted)}
.stat .v{font-size:22px;font-weight:700;margin-top:2px}
.stat .v.g{color:var(--green)} .stat .v.r{color:var(--red)} .stat .v.gd{color:var(--gold)} .stat .v.b{color:var(--blue)}
.controls{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:14px 0 6px}
.tabs{display:flex;flex-wrap:wrap;gap:6px}
.tab{background:var(--panel2);border:1px solid var(--line);color:var(--muted);border-radius:999px;padding:6px 14px;font-size:13px;cursor:pointer}
.tab.active{background:var(--gold);color:#1a1305;border-color:var(--gold);font-weight:700}
.tab .cnt{opacity:.7;font-size:11px;margin-left:3px}
input,select{background:var(--panel2);border:1px solid var(--line);color:var(--text);border-radius:8px;padding:7px 10px;font-size:13px}
input:focus,select:focus{outline:1px solid var(--gold)}
.league{font-size:14px;font-weight:700;color:var(--gold);margin:22px 0 8px;display:flex;align-items:center;gap:8px}
.league .n{background:rgba(245,196,81,.12);padding:3px 10px;border-radius:8px;border:1px solid rgba(245,196,81,.3)}
.league .c{color:var(--muted);font-weight:400;font-size:12px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:14px 16px;margin-bottom:10px;transition:border-color .15s}
.card:hover{border-color:#3b4b6b}
.row{display:flex;flex-wrap:wrap;align-items:center;gap:8px}
.meta{color:var(--muted);font-size:12px}
.teams{font-size:18px;font-weight:700;margin:8px 0 10px;display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.teams .vs{color:var(--muted);font-weight:400;font-size:13px}
.score{margin-left:auto;font-size:22px;font-weight:800;color:var(--green)}
.score .half{display:block;font-size:11px;color:var(--muted);font-weight:400;text-align:right}
.lines{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:10px}
.line{background:var(--panel2);border:1px solid var(--line);border-radius:10px;padding:10px 12px;display:flex;justify-content:space-between;align-items:center;gap:8px}
.line .lb{font-size:12px;color:var(--muted)}
.line .lp{font-size:14px;font-weight:700}
.line .odds{font-size:12px;color:var(--muted)}
.res{display:flex;gap:8px;margin-top:10px;flex-wrap:wrap}
.res .chip{font-size:13px;padding:4px 12px;border-radius:999px}
.res .chip .pl{font-weight:700;margin-left:6px}
details{margin-top:10px;font-size:12px;color:var(--muted)}
summary{cursor:pointer;color:var(--blue);font-size:12px}
details table{width:100%;border-collapse:collapse;margin-top:6px}
details td{padding:3px 8px;border-bottom:1px dashed var(--line);vertical-align:top}
details td:first-child{color:var(--muted);width:120px;white-space:nowrap}
footer{margin-top:30px;color:var(--muted);font-size:12px;text-align:center}
.empty{color:var(--muted);text-align:center;padding:40px 0}
@media (max-width:640px){.teams{font-size:16px}.score{font-size:18px}}
</style>
</head>
<body>
<div class="wrap">
<header>
  <h1>⚽ 足球每日台账</h1>
  <div class="sub" id="subtitle"></div>
</header>

<div class="stats" id="stats"></div>

<div class="controls">
  <div class="tabs" id="tabs"></div>
  <input id="q" type="search" placeholder="搜索球队 / 联赛…" style="flex:1;min-width:160px">
  <select id="leagueFilter"><option value="">全部联赛</option></select>
  <select id="statusFilter"><option value="">全部状态</option></select>
</div>

<div id="content"></div>
<footer id="footer"></footer>
</div>

<script>
const LEDGER = __DATA_JSON__;
const DAYS = Object.keys(LEDGER.days || {}).sort();
const PAY = {"赢":1,"赢半":0.5,"走水":0,"输半":-0.5,"输":-1};

function esc(s){return String(s==null?"":s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));}
function oddsOf(pick, i){const m=String(pick||"").match(/（([\d.]+)\/([\d.]+)）/);return m?parseFloat(m[i]):null;}
function pl(result, odds){if(!result||odds==null||!(result in PAY))return null;const b=PAY[result];return b>0?Math.round(b*odds*1000)/1000:b;}
function statusCls(s){return s==="已冻结"?"b-freeze":s==="进行中"?"b-live":s==="待赛果"?"b-pending":s==="已结算"?"b-done":"b-pending";}
function resCls(r){return r==="赢"?"b-win":r==="赢半"?"b-halfwin":r==="走水"?"b-push":r==="输半"?"b-halfloss":r==="输"?"b-loss":"b-push";}

let currentDay = DAYS[DAYS.length-1] || "";
let q="", league="", status="";

function allMatches(){const out=[];for(const d of DAYS){for(const m of (LEDGER.days[d]||{}).matches||[]){out.push({day:d,...m});}}return out;}

function dayMatches(day){return (LEDGER.days[day]||{}).matches||[];}

function computeStats(day){
  const ms=dayMatches(day);
  const st={freeze:0,live:0,pending:0,done:0,hp:{},ou:{},pl_h:0,pl_o:0};
  for(const m of ms){
    st[m.status==="已冻结"?"freeze":m.status==="进行中"?"live":m.status==="待赛果"?"pending":m.status==="已结算"?"done":m.status]=(st[m.status==="已冻结"?"freeze":m.status==="进行中"?"live":m.status==="待赛果"?"pending":m.status==="已结算"?"done":m.status]||0)+1;
    if(m.status==="已结算"){
      const oh=oddsOf(m.handicap_pick,0), oo=oddsOf(m.ou_pick,0);
      if(m.handicap_result){st.hp[m.handicap_result]=(st.hp[m.handicap_result]||0)+1;const p=pl(m.handicap_result,oh);if(p!=null)st.pl_h+=p;}
      if(m.ou_result){st.ou[m.ou_result]=(st.ou[m.ou_result]||0)+1;const p=pl(m.ou_result,oo);if(p!=null)st.pl_o+=p;}
    }
  }
  st.pl_h=Math.round(st.pl_h*1000)/1000; st.pl_o=Math.round(st.pl_o*1000)/1000;
  return st;
}

function overallStats(){
  const s={days:DAYS.length,match:0,done:0,hp:{},ou:{},pl_h:0,pl_o:0};
  for(const m of allMatches()){
    s.match++;
    if(m.status==="已结算"){
      s.done++;
      const oh=oddsOf(m.handicap_pick,0), oo=oddsOf(m.ou_pick,0);
      if(m.handicap_result){s.hp[m.handicap_result]=(s.hp[m.handicap_result]||0)+1;const p=pl(m.handicap_result,oh);if(p!=null)s.pl_h+=p;}
      if(m.ou_result){s.ou[m.ou_result]=(s.ou[m.ou_result]||0)+1;const p=pl(m.ou_result,oo);if(p!=null)s.pl_o+=p;}
    }
  }
  s.pl_h=Math.round(s.pl_h*1000)/1000; s.pl_o=Math.round(s.pl_o*1000)/1000;
  return s;
}

function renderTabs(){
  const el=document.getElementById("tabs");
  el.innerHTML="";
  for(const d of DAYS){
    const b=document.createElement("button");
    b.className="tab"+(d===currentDay?" active":"");
    b.textContent=d.slice(5)+" · "+dayMatches(d).length;
    b.onclick=()=>{currentDay=d;render();};
    el.appendChild(b);
  }
}

function renderStats(){
  const el=document.getElementById("stats");
  const st=computeStats(currentDay);
  const rec=(o)=>[["赢",o.win||0],["赢半",o.halfwin||0],["走水",o.push||0],["输半",o.halfloss||0],["输",o.loss||0]].map(([k,v])=>k+" "+v).join(" · ");
  const fmt=(x)=>x>0?("+"+x):String(x);
  const cards=[
    ["总场次",st.freeze+st.live+st.pending+st.done,"b",null],
    ["已结算",st.done,"g",null],
    ["待赛果",st.pending,"gd",null],
    ["让球战绩",rec(st.hp),"b",null],
    ["大小球战绩",rec(st.ou),"b",null],
    ["让球盈亏",fmt(st.pl_h)+" 注",st.pl_h>=0?"g":"r",null],
    ["大小球盈亏",fmt(st.pl_o)+" 注",st.pl_o>=0?"g":"r",null],
  ];
  el.innerHTML=cards.map(c=>`<div class="stat"><div class="k">${c[0]}</div><div class="v ${c[2]}">${c[1]}</div></div>`).join("");
}

function renderFilters(){
  const leagues=new Set(), statuses=new Set();
  for(const m of dayMatches(currentDay)){leagues.add(m.league||"未分类");statuses.add(m.status);}
  const lf=document.getElementById("leagueFilter"), sf=document.getElementById("statusFilter");
  const lv=lf.value, sv=sf.value;
  lf.innerHTML='<option value="">全部联赛</option>'+[...leagues].sort().map(x=>`<option>${esc(x)}</option>`).join("");
  sf.innerHTML='<option value="">全部状态</option>'+[...statuses].sort().map(x=>`<option>${esc(x)}</option>`).join("");
  if([...leagues].includes(lv))lf.value=lv; else league="";
  if([...statuses].includes(sv))sf.value=sv; else status="";
}

function matchCard(m){
  const hp=oddsOf(m.handicap_pick,0), op=oddsOf(m.ou_pick,0);
  const hpl=pl(m.handicap_result,hp), opl=pl(m.ou_result,op);
  const scoreBox=m.score?`<div class="score">${esc(m.score)}<span class="half">半场 ${esc(m.half||"-")}</span></div>`:"";
  const res=[];
  if(m.handicap_result)res.push(`<span class="chip ${resCls(m.handicap_result)}">让球 · ${esc(m.handicap_result)}<span class="pl">${hpl!=null?(hpl>=0?"+":"")+hpl:"-"}</span></span>`);
  if(m.ou_result)res.push(`<span class="chip ${resCls(m.ou_result)}">大小球 · ${esc(m.ou_result)}<span class="pl">${opl!=null?(opl>=0?"+":"")+opl:"-"}</span></span>`);
  const fenxi=m.fenxi_hash?`<a href="https://m.live.qtx.com/fenxi/${esc(m.fenxi_hash)}.html" target="_blank" rel="noopener">qtx 分析页 ↗</a>`:"-";
  return `<div class="card">
    <div class="row meta">
      <span>🕐 ${esc(m.kickoff||"-")}</span>
      <span>🏆 ${esc(m.league||m.league_raw||"-")}</span>
      <span class="badge ${statusCls(m.status)}">${esc(m.status)}</span>
      ${m.score?`<span>${esc(m.note||"")}</span>`:""}
    </div>
    <div class="teams"><span>${esc(m.home)}</span><span class="vs">vs</span><span>${esc(m.away)}</span>${scoreBox}</div>
    <div class="lines">
      <div class="line"><span><span class="lb">让球推荐</span><br><span class="lp">${esc(m.handicap_pick||"-")}</span></span>${m.handicap_pick&&m.handicap_pick!=="未开盘"?`<span class="odds">水位 ${esc(m.handicap_pick.replace(/^.*（/,"").replace(/）$/,""))}</span>`:""}</div>
      <div class="line"><span><span class="lb">大小球推荐</span><br><span class="lp">${esc(m.ou_pick||"-")}</span></span>${m.ou_pick&&m.ou_pick!=="未开盘"?`<span class="odds">水位 ${esc(m.ou_pick.replace(/^.*（/,"").replace(/）$/,""))}</span>`:""}</div>
    </div>
    ${res.length?`<div class="res">${res.join("")}</div>`:""}
    <details><summary>详情 / 来源信息</summary>
      <table>
        <tr><td>匹配键</td><td>${esc(m.match_key||"-")}</td></tr>
        <tr><td>qtx 比赛ID</td><td>${esc(m.qtx_id||"-")}</td></tr>
        <tr><td>赛事ID</td><td>${esc(m.competition_id||"-")}</td></tr>
        <tr><td>原始联赛</td><td>${esc(m.league_raw||"-")}</td></tr>
        <tr><td>开盘状态</td><td>${esc((m.optional||"").split(";").filter(x=>x.startsWith("status:")).join("; ")||"-")}</td></tr>
        <tr><td>分析页</td><td>${fenxi}</td></tr>
        <tr><td>备注</td><td>${esc(m.note||"-")}</td></tr>
        <tr><td>创建/更新</td><td>${esc(m.created_at||"-")} / ${esc(m.updated_at||"-")}</td></tr>
      </table>
    </details>
  </div>`;
}

function render(){
  renderStats(); renderTabs(); renderFilters();
  const el=document.getElementById("content");
  const ql=q.trim().toLowerCase();
  const ms=dayMatches(currentDay).filter(m=>{
    if(league&&m.league!==league)return false;
    if(status&&m.status!==status)return false;
    if(ql&&!(m.home.toLowerCase().includes(ql)||m.away.toLowerCase().includes(ql)||(m.league||"").toLowerCase().includes(ql)))return false;
    return true;
  });
  if(!ms.length){el.innerHTML='<div class="empty">该日期暂无符合条件的比赛</div>';return;}
  const groups={};
  for(const m of ms){(groups[m.league||"未分类"]=groups[m.league||"未分类"]||[]).push(m);}
  let html="";
  for(const lg of Object.keys(groups).sort()){
    const arr=groups[lg].slice().sort((a,b)=>(a.kickoff||"").localeCompare(b.kickoff||""));
    html+=`<div class="league"><span class="n">${esc(lg)}</span><span class="c">${arr.length} 场</span></div>`+arr.map(matchCard).join("");
  }
  el.innerHTML=html;
  const sub=document.getElementById("subtitle");
  sub.textContent=`北京时间自然日 · 数据存于 GitHub 仓库 · 最近更新 ${LEDGER.generated_at||"-"}`;
  const foot=document.getElementById("footer");
  foot.innerHTML=`共 ${DAYS.length} 个比赛日 · 生成于 ${LEDGER.generated_at||"-"} · 数据源 qtx（球天下）`;
}

document.getElementById("q").addEventListener("input",e=>{q=e.target.value;render();});
document.getElementById("leagueFilter").addEventListener("change",e=>{league=e.target.value;render();});
document.getElementById("statusFilter").addEventListener("change",e=>{status=e.target.value;render();});
render();
</script>
</body>
</html>
"""
