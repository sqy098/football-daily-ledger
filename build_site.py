#!/usr/bin/env python3
"""Generate a self-contained GitHub Pages site from stored daily JSON files.

Reads data/YYYY-MM-DD.json and writes index.html with an embedded dataset:
- summary stat cards,
- per-league profit table,
- per-team profit table,
- a Feishu-style sortable/filterable match list table.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Shanghai")


def generate_site(data_dir: Path, site_file: Path) -> None:
    days: dict[str, dict] = {}
    if data_dir.exists():
        for path in sorted(data_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8-sig"))
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
    print(f"build: wrote {site_file} ({len(html)} chars, {len(days)} days)")


TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>足球每日台账 · Asian Handicap Ledger</title>
<style>
:root{
  --bg:#0e1420; --panel:#171f2e; --panel2:#1d2739; --line:#2a3650; --line2:#33425f;
  --text:#e8eef7; --muted:#93a3bd; --gold:#f5c451; --green:#4ade80;
  --red:#f87171; --blue:#60a5fa;
}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);font-family:"Segoe UI",system-ui,"Microsoft YaHei",sans-serif;line-height:1.45;padding:20px 16px 60px}
.wrap{max-width:1280px;margin:0 auto}
header h1{font-size:24px;font-weight:700;letter-spacing:.5px}
header .sub{color:var(--muted);font-size:13px;margin-top:4px}
.badge{display:inline-block;padding:2px 9px;border-radius:999px;font-size:12px;font-weight:600;white-space:nowrap}
.b-freeze{background:rgba(96,165,250,.15);color:var(--blue);border:1px solid rgba(96,165,250,.4)}
.b-live{background:rgba(245,196,81,.15);color:var(--gold);border:1px solid rgba(245,196,81,.4)}
.b-pending{background:rgba(147,163,189,.12);color:var(--muted);border:1px solid rgba(147,163,189,.35)}
.b-done{background:rgba(74,222,128,.13);color:var(--green);border:1px solid rgba(74,222,128,.4)}
.b-win{background:rgba(74,222,128,.15);color:var(--green)}
.b-halfwin{background:rgba(74,222,128,.08);color:#86efac}
.b-push{background:rgba(147,163,189,.12);color:#cbd5e1}
.b-halfloss{background:rgba(248,113,113,.1);color:#fca5a5}
.b-loss{background:rgba(248,113,113,.17);color:var(--red)}
.pos{color:var(--green);font-weight:700}
.neg{color:var(--red);font-weight:700}
.zero{color:var(--muted)}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:18px 0}
.stat{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:12px 14px}
.stat .k{font-size:12px;color:var(--muted)}
.stat .v{font-size:22px;font-weight:700;margin-top:2px}
.stat .v.g{color:var(--green)} .stat .v.r{color:var(--red)} .stat .v.gd{color:var(--gold)} .stat .v.b{color:var(--blue)}
.stat .v.small{font-size:15px;font-weight:600;margin-top:4px}
.controls{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:16px 0 8px}
.tabs{display:flex;flex-wrap:wrap;gap:6px}
.tab{background:var(--panel2);border:1px solid var(--line);color:var(--muted);border-radius:999px;padding:6px 14px;font-size:13px;cursor:pointer}
.tab.active{background:var(--gold);color:#1a1305;border-color:var(--gold);font-weight:700}
.tab .cnt{opacity:.7;font-size:11px;margin-left:3px}
input,select{background:var(--panel2);border:1px solid var(--line);color:var(--text);border-radius:8px;padding:7px 10px;font-size:13px}
input:focus,select:focus{outline:1px solid var(--gold)}
h2.sec{font-size:16px;font-weight:700;margin:26px 0 10px;color:var(--gold);display:flex;align-items:center;gap:8px}
h2.sec::before{content:"";width:4px;height:16px;background:var(--gold);border-radius:2px}
.tablebox{background:var(--panel);border:1px solid var(--line);border-radius:12px;overflow:auto;max-height:460px}
table{width:100%;border-collapse:collapse;font-size:13px;min-width:640px}
thead th{position:sticky;top:0;background:var(--panel2);color:var(--muted);font-weight:600;text-align:left;padding:9px 12px;border-bottom:1px solid var(--line2);white-space:nowrap;cursor:pointer;user-select:none;z-index:1}
thead th:hover{color:var(--gold)}
thead th .arr{opacity:.6;font-size:11px}
tbody td{padding:8px 12px;border-bottom:1px solid var(--line);vertical-align:middle;white-space:nowrap}
tbody tr:hover{background:rgba(245,196,81,.04)}
tr.r-done td{background:rgba(74,222,128,.03)}
td.home{text-align:right}
td.score{text-align:center;font-weight:800}
td.score .half{display:block;font-size:10px;color:var(--muted);font-weight:400}
td.away{text-align:left}
td.num{text-align:right;font-variant-numeric:tabular-nums}
tr.detail-row td{background:var(--panel2);font-size:12px;color:var(--muted);white-space:normal}
.detail-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:4px 24px}
.detail-grid span b{color:var(--muted);font-weight:500}
.detail-grid a{color:var(--blue);text-decoration:none}
.btn-detail{background:none;border:1px solid var(--line);color:var(--muted);border-radius:6px;padding:2px 8px;font-size:12px;cursor:pointer}
.btn-detail:hover{color:var(--gold);border-color:var(--gold)}
footer{margin-top:30px;color:var(--muted);font-size:12px;text-align:center}
.empty{color:var(--muted);text-align:center;padding:40px 0}
@media (max-width:760px){.teams{font-size:15px}}
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
  <input id="q" type="search" placeholder="搜索球队 / 联赛…" style="flex:1;min-width:170px">
  <select id="leagueFilter"><option value="">全部联赛</option></select>
  <select id="statusFilter"><option value="">全部状态</option></select>
</div>

<h2 class="sec">联赛盈利统计</h2>
<div class="tablebox"><table id="leagueStats">
  <thead><tr><th>联赛</th><th>场次</th><th>已结算</th><th>让球战绩</th><th>大小球战绩</th><th class="num">让球盈亏</th><th class="num">大小球盈亏</th><th class="num">合计</th></tr></thead>
  <tbody></tbody>
</table></div>

<h2 class="sec">球队盈利统计</h2>
<div class="tablebox"><table id="teamStats">
  <thead><tr><th>球队</th><th>场次</th><th>让球战绩</th><th>大小球战绩</th><th class="num">让球盈亏</th><th class="num">大小球盈亏</th><th class="num">总盈亏</th></tr></thead>
  <tbody></tbody>
</table></div>

<h2 class="sec">比赛列表 <span id="tableCount" style="font-weight:400;font-size:13px;color:var(--muted)"></span></h2>
<div class="tablebox"><table id="matchTable">
  <thead><tr>
    <th data-k="kickoff">开球时间<span class="arr"></span></th>
    <th data-k="league">联赛<span class="arr"></span></th>
    <th>主队</th>
    <th>比分</th>
    <th>客队</th>
    <th data-k="handicap_pick">让球推荐<span class="arr"></span></th>
    <th data-k="ou_pick">大小球推荐<span class="arr"></span></th>
    <th data-k="status">状态<span class="arr"></span></th>
    <th data-k="handicap_result">让球结论<span class="arr"></span></th>
    <th data-k="ou_result">大小球结论<span class="arr"></span></th>
    <th>详情</th>
  </tr></thead>
  <tbody></tbody>
</table></div>

<footer id="footer"></footer>
</div>

<script>
const LEDGER = __DATA_JSON__;
const DAYS = Object.keys(LEDGER.days || {}).sort();
const PAY = {"赢":1,"赢半":0.5,"走水":0,"输半":-0.5,"输":-1};

function esc(s){return String(s==null?"":s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));}
function oddsOf(pick,i){const m=String(pick||"").match(/（([\d.]+)\/([\d.]+)）/);return m?parseFloat(m[i+1]):null;}
function pl(result,odds){if(!result||odds==null||!(result in PAY))return null;const b=PAY[result];return b>0?Math.round(b*odds*1000)/1000:b;}
function fmt(x){if(x==null)return "-";return x>0?("+"+x):String(x);}
function clsNum(x){if(x==null)return "";return x>0?"pos":x<0?"neg":"zero";}
function statusCls(s){return s==="已冻结"?"b-freeze":s==="进行中"?"b-live":s==="待赛果"?"b-pending":s==="已结算"?"b-done":"b-pending";}
function resCls(r){return r==="赢"?"b-win":r==="赢半"?"b-halfwin":r==="走水"?"b-push":r==="输半"?"b-halfloss":r==="输"?"b-loss":"b-push";}
function rec(o){return ["赢","赢半","走水","输半","输"].map(c=>c+" "+(o[c]||0)).join(" · ");}

let scope = DAYS.length ? "all" : "";
let q="", league="", status="";
let sortKey="kickoff", sortDir=1;

function matchesIn(day){return (LEDGER.days[day]||{}).matches||[];}
function allMatches(){const out=[];for(const d of DAYS){for(const m of matchesIn(d))out.push({day:d,...m});}return out;}
function scopeMatches(){return scope==="all"?allMatches():matchesIn(scope);}
function filtered(){
  const ql=q.trim().toLowerCase();
  return scopeMatches().filter(m=>{
    if(league&&m.league!==league)return false;
    if(status&&m.status!==status)return false;
    if(ql&&!(m.home.toLowerCase().includes(ql)||m.away.toLowerCase().includes(ql)||(m.league||"").toLowerCase().includes(ql)))return false;
    return true;
  });
}
function accumulate(list){
  const s={total:0,done:0,hp:{},ou:{},pl_h:0,pl_o:0};
  for(const m of list){
    s.total++;
    if(m.status==="已结算"){
      s.done++;
      const oh=oddsOf(m.handicap_pick,0),oo=oddsOf(m.ou_pick,0);
      if(m.handicap_result){s.hp[m.handicap_result]=(s.hp[m.handicap_result]||0)+1;const p=pl(m.handicap_result,oh);if(p!=null)s.pl_h+=p;}
      if(m.ou_result){s.ou[m.ou_result]=(s.ou[m.ou_result]||0)+1;const p=pl(m.ou_result,oo);if(p!=null)s.pl_o+=p;}
    }
  }
  s.pl_h=Math.round(s.pl_h*1000)/1000;s.pl_o=Math.round(s.pl_o*1000)/1000;s.pl_sum=Math.round((s.pl_h+s.pl_o)*1000)/1000;
  return s;
}

function renderTabs(){
  const el=document.getElementById("tabs");el.innerHTML="";
  const mk=(label,val,cnt)=>{const b=document.createElement("button");b.className="tab"+(scope===val?" active":"");b.innerHTML=label+(cnt!=null?`<span class="cnt">${cnt}</span>`:"");b.onclick=()=>{scope=val;render();};el.appendChild(b);};
  mk("全部", "all", allMatches().length);
  for(const d of DAYS)mk(d.slice(5), d, matchesIn(d).length);
}
function renderStats(list){
  const el=document.getElementById("stats");const s=accumulate(list);
  const cards=[
    ["总场次",s.total,"b",null],
    ["已结算",s.done,"g",null],
    ["待赛果",s.total-s.done-s.freeze-s.live,"gd",null],
    ["让球战绩",rec(s.hp),"b","small"],
    ["大小球战绩",rec(s.ou),"b","small"],
    ["让球盈亏",fmt(s.pl_h)+" 注",s.pl_h>=0?"g":"r",null],
    ["大小球盈亏",fmt(s.pl_o)+" 注",s.pl_o>=0?"g":"r",null],
    ["合计盈亏",fmt(s.pl_sum)+" 注",s.pl_sum>=0?"g":"r",null],
  ];
  el.innerHTML=cards.map(c=>`<div class="stat"><div class="k">${c[0]}</div><div class="v ${c[2]} ${c[3]||""}">${c[1]}</div></div>`).join("");
}
function renderLeagueStats(list){
  const groups={};
  for(const m of list){(groups[m.league||"未分类"]=groups[m.league||"未分类"]||[]).push(m);}
  const rows=[];
  for(const lg of Object.keys(groups)){
    const s=accumulate(groups[lg]);
    rows.push({lg, s, key:(s.pl_sum||0)});
  }
  rows.sort((a,b)=>b.key-a.key);
  const tb=document.querySelector("#leagueStats tbody");
  tb.innerHTML=rows.map(r=>`<tr>
    <td>${esc(r.lg)}</td><td class="num">${r.s.total}</td><td class="num">${r.s.done}</td>
    <td>${rec(r.s.hp)}</td><td>${rec(r.s.ou)}</td>
    <td class="num ${clsNum(r.s.pl_h)}">${fmt(r.s.pl_h)}</td>
    <td class="num ${clsNum(r.s.pl_o)}">${fmt(r.s.pl_o)}</td>
    <td class="num ${clsNum(r.s.pl_sum)}">${fmt(r.s.pl_sum)}</td>
  </tr>`).join("")||'<tr><td colspan="8" class="empty">暂无数据</td></tr>';
}
function renderTeamStats(list){
  const groups={};
  for(const m of list){
    (groups[m.home]=groups[m.home]||[]).push({...m,side:"主"});
    (groups[m.away]=groups[m.away]||[]).push({...m,side:"客"});
  }
  const rows=[];
  for(const team of Object.keys(groups)){
    const ms=groups[team];const s=accumulate(ms);
    rows.push({team, n:ms.length, s, key:(s.pl_sum||0)});
  }
  rows.sort((a,b)=>b.key-a.key);
  const tb=document.querySelector("#teamStats tbody");
  tb.innerHTML=rows.slice(0,60).map(r=>`<tr>
    <td>${esc(r.team)}</td><td class="num">${r.n}</td>
    <td>${rec(r.s.hp)}</td><td>${rec(r.s.ou)}</td>
    <td class="num ${clsNum(r.s.pl_h)}">${fmt(r.s.pl_h)}</td>
    <td class="num ${clsNum(r.s.pl_o)}">${fmt(r.s.pl_o)}</td>
    <td class="num ${clsNum(r.s.pl_sum)}">${fmt(r.s.pl_sum)}</td>
  </tr>`).join("")||'<tr><td colspan="7" class="empty">暂无数据</td></tr>';
}
function renderFilters(){
  const leagues=new Set(),statuses=new Set();
  for(const m of scopeMatches()){leagues.add(m.league||"未分类");statuses.add(m.status);}
  const lf=document.getElementById("leagueFilter"),sf=document.getElementById("statusFilter");
  const lv=lf.value,sv=sf.value;
  lf.innerHTML='<option value="">全部联赛</option>'+[...leagues].sort().map(x=>`<option>${esc(x)}</option>`).join("");
  sf.innerHTML='<option value="">全部状态</option>'+[...statuses].sort().map(x=>`<option>${esc(x)}</option>`).join("");
  if([...leagues].includes(lv))lf.value=lv;else league="";
  if([...statuses].includes(sv))sf.value=sv;else status="";
}
function valOf(m,k){
  if(k==="kickoff")return m.kickoff||"";
  if(k==="league")return m.league||m.league_raw||"";
  if(k==="status")return m.status||"";
  if(k==="handicap_result"||k==="ou_result")return m[k]?PAY[m[k]]??0:0;
  return String(m[k]||"");
}
function matchRow(m,idx){
  const oh=oddsOf(m.handicap_pick,0),oo=oddsOf(m.ou_pick,0);
  const hpl=pl(m.handicap_result,oh),opl=pl(m.ou_result,oo);
  const hcl=resCls(m.handicap_result),ocl=resCls(m.ou_result);
  const score=m.score?`${esc(m.score)}<span class="half">半 ${esc(m.half||"-")}</span>`:"-";
  const fenxi=m.fenxi_hash?`<a href="https://m.live.qtx.com/fenxi/${esc(m.fenxi_hash)}.html" target="_blank" rel="noopener">分析页 ↗</a>`:"-";
  const note=m.note||"-";
  const open=(m.optional||"").split(";").filter(x=>x.startsWith("status:")).join("; ")||"-";
  return `<tr class="r-${m.status==="已结算"?"done":""}">
    <td>${esc(m.kickoff||"-")}</td>
    <td>${esc(m.league||m.league_raw||"-")}</td>
    <td class="home">${esc(m.home)}</td>
    <td class="score">${score}</td>
    <td class="away">${esc(m.away)}</td>
    <td>${esc(m.handicap_pick||"-")}</td>
    <td>${esc(m.ou_pick||"-")}</td>
    <td><span class="badge ${statusCls(m.status)}">${esc(m.status)}</span></td>
    <td>${m.handicap_result?`<span class="badge ${hcl}">${esc(m.handicap_result)}</span> <span class="num ${clsNum(hpl)}">${hpl!=null?fmt(hpl):""}</span>`:"-"}</td>
    <td>${m.ou_result?`<span class="badge ${ocl}">${esc(m.ou_result)}</span> <span class="num ${clsNum(opl)}">${opl!=null?fmt(opl):""}</span>`:"-"}</td>
    <td><button class="btn-detail" data-idx="${idx}">▸ 详情</button></td>
  </tr>
  <tr class="detail-row" id="detail-${idx}" style="display:none"><td colspan="11">
    <div class="detail-grid">
      <span><b>比赛日：</b>${esc(m.day||"-")}</span>
      <span><b>qtx ID：</b>${esc(m.qtx_id||"-")}</span>
      <span><b>赛事ID：</b>${esc(m.competition_id||"-")}</span>
      <span><b>原始联赛：</b>${esc(m.league_raw||"-")}</span>
      <span><b>开盘状态：</b>${esc(open)}</span>
      <span><b>分析页：</b>${fenxi}</span>
      <span><b>备注：</b>${esc(note)}</span>
      <span><b>创建/更新：</b>${esc(m.created_at||"-")} / ${esc(m.updated_at||"-")}</span>
    </div>
  </tr>`;
}
function renderTable(list){
  const sorted=list.slice().sort((a,b)=>{const va=valOf(a,sortKey),vb=valOf(b,sortKey);if(typeof va==="number"&&typeof vb==="number")return (va-vb)*sortDir;return String(va).localeCompare(String(vb),"zh")*sortDir;});
  const tb=document.querySelector("#matchTable tbody");
  tb.innerHTML=sorted.map((m,i)=>matchRow(m,i)).join("")||'<tr><td colspan="11" class="empty">暂无符合条件的比赛</td></tr>';
  document.querySelectorAll("#matchTable thead th[data-k]").forEach(th=>{
    const k=th.dataset.k;th.querySelector(".arr").textContent=(k===sortKey?(sortDir===1?"▲":"▼"):"");
  });
  document.getElementById("tableCount").textContent=`共 ${sorted.length} 场`;
  document.querySelectorAll(".btn-detail").forEach(b=>{
    b.onclick=()=>{const tr=document.getElementById("detail-"+b.dataset.idx);const show=tr.style.display==="none";tr.style.display=show?"":"none";b.textContent=show?"▾ 详情":"▸ 详情";};
  });
}
function render(){
  const list=filtered();
  renderStats(list);renderLeagueStats(list);renderTeamStats(list);renderTable(list);
  renderTabs();renderFilters();
  const sub=document.getElementById("subtitle");
  sub.textContent=`北京时间自然日 · 数据存于 GitHub 仓库 · 最近更新 ${LEDGER.generated_at||"-"}`;
  const foot=document.getElementById("footer");
  foot.innerHTML=`共 ${DAYS.length} 个比赛日 · ${allMatches().length} 场比赛 · 生成于 ${LEDGER.generated_at||"-"} · 数据源 qtx（球天下）`;
}
document.getElementById("q").addEventListener("input",e=>{q=e.target.value;render();});
document.getElementById("leagueFilter").addEventListener("change",e=>{league=e.target.value;render();});
document.getElementById("statusFilter").addEventListener("change",e=>{status=e.target.value;render();});
document.querySelectorAll("#matchTable thead th[data-k]").forEach(th=>{
  th.onclick=()=>{const k=th.dataset.k;if(sortKey===k){sortDir*=-1;}else{sortKey=k;sortDir=1;}render();};
});
render();
</script>
</body>
</html>
"""

