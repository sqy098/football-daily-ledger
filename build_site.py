#!/usr/bin/env python3
"""Generate a self-contained GitHub Pages site from stored daily JSON files.

Layout:
- top: Feishu-style dashboard (big-number cards + SVG charts:
  daily trend, win/loss distribution, league profit TOP, team profit TOP)
- bottom: Feishu-style sortable/filterable match list table (matches only).
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
<title>足球每日台账 · Dashboard</title>
<style>
:root{
  --bg:#0e1420; --panel:#171f2e; --panel2:#1d2739; --line:#2a3650; --line2:#33425f;
  --text:#e8eef7; --muted:#93a3bd; --gold:#f5c451; --green:#4ade80;
  --red:#f87171; --blue:#60a5fa; --purple:#c084fc;
}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);font-family:"Segoe UI",system-ui,"Microsoft YaHei",sans-serif;line-height:1.45;padding:20px 16px 60px}
.wrap{max-width:1280px;margin:0 auto}
header{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:10px}
header h1{font-size:23px;font-weight:700;letter-spacing:.5px}
header .sub{color:var(--muted);font-size:12px;margin-top:3px}
.tabs{display:flex;flex-wrap:wrap;gap:6px}
.tab{background:var(--panel2);border:1px solid var(--line);color:var(--muted);border-radius:999px;padding:6px 14px;font-size:13px;cursor:pointer}
.tab.active{background:var(--gold);color:#1a1305;border-color:var(--gold);font-weight:700}
.tab .cnt{opacity:.7;font-size:11px;margin-left:3px}
.dash{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px;margin:18px 0}
.kpi{background:linear-gradient(180deg,var(--panel2),var(--panel));border:1px solid var(--line);border-radius:14px;padding:14px 16px;position:relative;overflow:hidden}
.kpi::before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--accent,var(--blue))}
.kpi .k{font-size:12px;color:var(--muted)}
.kpi .v{font-size:26px;font-weight:800;margin-top:4px;font-variant-numeric:tabular-nums}
.kpi .s{font-size:11px;color:var(--muted);margin-top:3px}
.kpi[data-click]{cursor:pointer}
.kpi[data-click]:hover{outline:1px solid var(--gold)}
.v.g{color:var(--green)} .v.r{color:var(--red)} .v.gd{color:var(--gold)} .v.b{color:var(--blue)}
.charts{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:12px;margin:6px 0 18px}
.chart{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px}
.chart h3{font-size:14px;font-weight:700;color:var(--gold);margin-bottom:12px}
.chart.wide{grid-column:1/-1}
.legend{display:flex;flex-wrap:wrap;gap:4px 14px;margin-top:10px;font-size:11px;color:var(--muted)}
.legend i{display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:4px;vertical-align:-1px}
.hbars{display:flex;flex-direction:column;gap:7px}
.hbar{display:grid;grid-template-columns:150px 1fr 70px;align-items:center;gap:10px;font-size:12px}
.hbar .l{color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.hbar .track{background:var(--panel2);border-radius:6px;height:16px;position:relative;overflow:hidden}
.hbar .fill{position:absolute;top:0;bottom:0;left:0;border-radius:6px}
.hbar .fill.pos{background:linear-gradient(90deg,#22c55e,var(--green))}
.hbar .fill.neg{background:linear-gradient(90deg,#ef4444,var(--red))}
.hbar .v{text-align:right;font-weight:700;font-variant-numeric:tabular-nums}
.hbar{cursor:pointer;border-radius:8px;padding:0 4px;transition:background .15s}
.hbar:hover{background:rgba(245,196,81,.07)}
.hbar:hover .l{color:var(--gold)}
.pos{color:var(--green)} .neg{color:var(--red)} .zero{color:var(--muted)}
.vbars{display:flex;align-items:flex-end;gap:8px;height:150px;padding-top:6px}
.vbar{flex:1;display:flex;flex-direction:column;align-items:center;height:100%;min-width:26px}
.vbar .col{flex:1;width:100%;display:flex;align-items:flex-end;justify-content:center}
.vbar .fill{width:60%;border-radius:5px 5px 0 0;min-height:2px}
.vbar .fill.pos{background:linear-gradient(180deg,var(--green),#22c55e)}
.vbar .fill.neg{background:linear-gradient(180deg,var(--red),#ef4444)}
.vbar .val{font-size:10px;color:var(--muted);margin-top:4px}
.vbar .lab{font-size:10px;color:var(--muted);margin-top:2px;white-space:nowrap}
.donuts{display:flex;flex-wrap:wrap;gap:16px;justify-content:space-around}
.donut{text-align:center}
.donut .lbl{font-size:12px;color:var(--muted);margin-top:6px}
h2.sec{font-size:17px;font-weight:700;margin:8px 0 12px;color:var(--gold);display:flex;align-items:center;gap:8px}
h2.sec::before{content:"";width:4px;height:17px;background:var(--gold);border-radius:2px}
.controls{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:0 0 10px}
input,select{background:var(--panel2);border:1px solid var(--line);color:var(--text);border-radius:8px;padding:7px 10px;font-size:13px}
input:focus,select:focus{outline:1px solid var(--gold)}
.tablebox{background:var(--panel);border:1px solid var(--line);border-radius:12px;overflow:auto;max-height:520px}
table{width:100%;border-collapse:collapse;font-size:13px;min-width:900px}
thead th{position:sticky;top:0;background:var(--panel2);color:var(--muted);font-weight:600;text-align:left;padding:9px 12px;border-bottom:1px solid var(--line2);white-space:nowrap;cursor:pointer;user-select:none;z-index:1}
thead th:hover{color:var(--gold)}
thead th .arr{opacity:.6;font-size:11px}
tbody td{padding:8px 12px;border-bottom:1px solid var(--line);vertical-align:middle;white-space:nowrap}
tbody tr:hover{background:rgba(245,196,81,.04)}
td.home{text-align:right}
td.score{text-align:center;font-weight:800}
td.score .half{display:block;font-size:10px;color:var(--muted);font-weight:400}
td.away{text-align:left}
td.num{text-align:right;font-variant-numeric:tabular-nums}
tr.detail-row td{background:var(--panel2);font-size:12px;color:var(--muted);white-space:normal}
.detail-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:4px 24px}
.detail-grid span b{color:var(--muted);font-weight:500}
.detail-grid a{color:var(--blue);text-decoration:none}
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
.btn-detail{background:none;border:1px solid var(--line);color:var(--muted);border-radius:6px;padding:2px 8px;font-size:12px;cursor:pointer}
.btn-detail:hover{color:var(--gold);border-color:var(--gold)}
.drawer{position:fixed;inset:0;background:rgba(6,10,18,.72);display:none;align-items:flex-start;justify-content:center;padding:36px 14px;z-index:50;overflow:auto}
.drawer.open{display:flex}
.drawer-card{background:var(--panel);border:1px solid var(--line2);border-radius:16px;max-width:1120px;width:100%;padding:18px 20px;box-shadow:0 24px 70px rgba(0,0,0,.55)}
.drawer-head{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:12px}
.drawer-head h3{font-size:18px;color:var(--gold)}
.drawer-close{background:none;border:1px solid var(--line);color:var(--muted);border-radius:8px;padding:4px 12px;cursor:pointer;font-size:13px}
.drawer-close:hover{color:var(--gold);border-color:var(--gold)}
.drawer-kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:8px;margin-bottom:14px}
.drawer-kpi{background:var(--panel2);border:1px solid var(--line);border-radius:10px;padding:8px 12px}
.drawer-kpi .k{font-size:11px;color:var(--muted)}
.drawer-kpi .v{font-size:17px;font-weight:800}
.drawer-table{max-height:440px;overflow:auto}
.drawer-table table{min-width:1000px}
.drawer-table .hl{color:var(--gold);font-weight:700}
footer{margin-top:28px;color:var(--muted);font-size:12px;text-align:center}
.empty{color:var(--muted);text-align:center;padding:40px 0}
</style>
</head>
<body>
<div class="wrap">
<header>
  <div>
    <h1>⚽ 足球每日台账</h1>
    <div class="sub" id="subtitle"></div>
  </div>
  <div class="tabs" id="tabs"></div>
</header>

<div class="dash" id="kpis"></div>

<div class="charts">
  <div class="chart"><h3>每日场次</h3><div id="chartDays" class="vbars"></div></div>
  <div class="chart"><h3>每日盈亏</h3><div id="chartProfit" class="vbars"></div></div>
  <div class="chart"><h3>让球战绩分布</h3><div id="chartHp" class="donuts"></div></div>
  <div class="chart"><h3>大小球战绩分布</h3><div id="chartOu" class="donuts"></div></div>
  <div class="chart wide"><h3>联赛盈利 TOP 10</h3><div id="chartLeague" class="hbars"></div></div>
  <div class="chart wide"><h3>球队盈利 TOP 10</h3><div id="chartTeam" class="hbars"></div></div>
</div>

<h2 class="sec">比赛列表 <span id="tableCount" style="font-weight:400;font-size:13px;color:var(--muted)"></span></h2>
<div class="controls">
  <input id="q" type="search" placeholder="搜索球队 / 联赛…" style="flex:1;min-width:170px">
  <select id="leagueFilter"><option value="">全部联赛</option></select>
  <select id="statusFilter"><option value="">全部状态</option></select>
</div>
<div class="tablebox"><table id="matchTable">
  <thead><tr>
    <th data-k="kickoff">开球时间<span class="arr"></span></th>
    <th data-k="league">联赛<span class="arr"></span></th>
    <th>主队</th><th>比分</th><th>客队</th>
    <th data-k="handicap_pick">让球推荐<span class="arr"></span></th>
    <th data-k="ou_pick">大小球推荐<span class="arr"></span></th>
    <th data-k="status">状态<span class="arr"></span></th>
    <th data-k="handicap_result">让球结论<span class="arr"></span></th>
    <th data-k="ou_result">大小球结论<span class="arr"></span></th>
    <th>详情</th>
  </tr></thead>
  <tbody></tbody>
</table></div>

<div class="drawer" id="drawer">
  <div class="drawer-card">
    <div class="drawer-head"><h3 id="drawerTitle"></h3><button class="drawer-close" id="drawerClose">✕ 关闭</button></div>
    <div class="drawer-kpis" id="drawerKpis"></div>
    <div class="drawer-table"><table id="drawerTable">
      <thead><tr>
        <th>日期</th><th>主队</th><th>比分</th><th>客队</th>
        <th>让球推荐</th><th>让球结果</th><th>让球盈亏</th>
        <th>大小球推荐</th><th>大小球结果</th><th>大小球盈亏</th>
        <th>总盈亏</th><th>状态</th>
      </tr></thead>
      <tbody></tbody>
    </table></div>
  </div>
</div>
<footer id="footer"></footer>
</div>

<script>
const LEDGER = __DATA_JSON__;
const DAYS = Object.keys(LEDGER.days || {}).sort();
const PAY = {"赢":1,"赢半":0.5,"走水":0,"输半":-0.5,"输":-1};
const COLORS = {"赢":"#4ade80","赢半":"#86efac","走水":"#94a3b8","输半":"#fca5a5","输":"#f87171"};

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
let CUR_LIST=[];

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
  const s={total:0,done:0,freeze:0,live:0,hp:{},ou:{},pl_h:0,pl_o:0};
  for(const m of list){
    s.total++;
    if(m.status==="已结算"){s.done++;}
    else if(m.status==="进行中"){s.live++;}
    else if(m.status==="已冻结"){s.freeze++;}
    const oh=oddsOf(m.handicap_pick,0),oo=oddsOf(m.ou_pick,0);
    if(m.handicap_result){s.hp[m.handicap_result]=(s.hp[m.handicap_result]||0)+1;const p=pl(m.handicap_result,oh);if(p!=null)s.pl_h+=p;}
    if(m.ou_result){s.ou[m.ou_result]=(s.ou[m.ou_result]||0)+1;const p=pl(m.ou_result,oo);if(p!=null)s.pl_o+=p;}
  }
  s.pl_h=Math.round(s.pl_h*1000)/1000;s.pl_o=Math.round(s.pl_o*1000)/1000;s.pl_sum=Math.round((s.pl_h+s.pl_o)*1000)/1000;
  const hd=(s.hp["赢"]||0)+(s.hp["赢半"]||0), ht=(s.hp["输"]||0)+(s.hp["输半"]||0);
  const od=(s.ou["赢"]||0)+(s.ou["赢半"]||0), ot=(s.ou["输"]||0)+(s.ou["输半"]||0);
  s.hp_rate=hd+ht?Math.round(hd/(hd+ht)*1000)/10:null;
  s.ou_rate=od+ot?Math.round(od/(od+ot)*1000)/10:null;
  return s;
}
function donut(el, parts, center1, center2){
  const total=parts.reduce((a,p)=>a+p.value,0)||1;
  let acc=0;const r=34,c=2*Math.PI*r;let segs="";
  for(const p of parts){if(p.value<=0)continue;const len=p.value/total*c;segs+=`<circle r="${r}" cx="60" cy="60" fill="none" stroke="${p.color}" stroke-width="15" stroke-dasharray="${len} ${c-len}" stroke-dashoffset="${-acc*c}" transform="rotate(-90 60 60)"><title>${esc(p.label)} ${p.value}</title></circle>`;acc+=p.value/total;}
  el.innerHTML=`<div class="donut"><svg viewBox="0 0 120 120" width="128" height="128">${segs||'<circle r="34" cx="60" cy="60" fill="none" stroke="#2a3650" stroke-width="15"/>'}<text x="60" y="56" text-anchor="middle" font-size="14" font-weight="800" fill="#e8eef7">${center1}</text><text x="60" y="72" text-anchor="middle" font-size="9" fill="#93a3bd">${center2}</text></svg><div class="lbl">${parts.map(p=>`<span style="white-space:nowrap"><i style="background:${p.color}"></i>${esc(p.label)} ${p.value}</span>`).join(" ")}</div></div>`;
}
function hbars(el, items, onClick){
  const max=Math.max(...items.map(i=>Math.abs(i.value)),1);
  el.innerHTML=items.map(it=>`<div class="hbar"${onClick?` data-k="${esc(it.label)}"`:` role="button"`}><div class="l" title="${esc(it.label)}">${esc(it.label)}</div><div class="track"><div class="fill ${it.value>=0?"pos":"neg"}" style="width:${Math.max(1.5,Math.abs(it.value)/max*100)}%"></div></div><div class="v ${clsNum(it.value)}">${fmt(it.value)}</div></div>`).join("")||'<div class="empty">暂无数据</div>';
  if(onClick)el.querySelectorAll(".hbar").forEach(row=>row.onclick=()=>onClick(row.dataset.k));
}
function vbars(el, items){
  const max=Math.max(...items.map(i=>Math.abs(i.value)),1);
  el.innerHTML=items.map(it=>`<div class="vbar"><div class="col"><div class="fill ${it.value>=0?"pos":"neg"}" style="height:${Math.max(2,Math.abs(it.value)/max*100)}%"></div></div><div class="val">${it.label2!=null?fmt(it.label2):""}</div><div class="lab">${esc(it.label)}</div></div>`).join("")||'<div class="empty">暂无数据</div>';
}

function renderTabs(){
  const el=document.getElementById("tabs");el.innerHTML="";
  const mk=(label,val,cnt)=>{const b=document.createElement("button");b.className="tab"+(scope===val?" active":"");b.innerHTML=label+(cnt!=null?`<span class="cnt">${cnt}</span>`:"");b.onclick=()=>{scope=val;render();};el.appendChild(b);};
  mk("📊 全部","all",allMatches().length);
  for(const d of DAYS)mk(d.slice(5),d,matchesIn(d).length);
}
function renderKPIs(list){
  const s=accumulate(list);
  const kpis=[
    ["总场次",s.total,s.freeze+" 冻结 · "+s.live+" 进行中",null,"var(--blue)"],
    ["已结算",s.done,(s.total?s.done/s.total*100:0).toFixed(1)+"%",null,"var(--green)"],
    ["让球胜率",s.hp_rate==null?"-":s.hp_rate+"%","赢"+(s.hp["赢"]||0)+" 赢半"+(s.hp["赢半"]||0)+" 输"+(s.hp["输"]||0),"b","var(--gold)"],
    ["大小球胜率",s.ou_rate==null?"-":s.ou_rate+"%","赢"+(s.ou["赢"]||0)+" 赢半"+(s.ou["赢半"]||0)+" 输"+(s.ou["输"]||0),"b","var(--gold)"],
    ["让球盈亏",fmt(s.pl_h)+" 注",rec(s.hp),s.pl_h>=0?"g":"r","var(--green)","hp"],
    ["大小球盈亏",fmt(s.pl_o)+" 注",rec(s.ou),s.pl_o>=0?"g":"r","var(--green)","ou"],
    ["总盈亏",fmt(s.pl_sum)+" 注",(s.done?((s.pl_sum/s.done).toFixed(2)):"0")+" / 场",s.pl_sum>=0?"g":"r","var(--green)","sum"],
  ];
  document.getElementById("kpis").innerHTML=kpis.map(k=>`<div class="kpi"${k[5]?` data-click="${k[5]}"`:""} style="--accent:${k[4]}"><div class="k">${k[0]}</div><div class="v ${k[3]}">${k[1]}</div><div class="s">${k[2]}</div></div>`).join("");
  document.querySelectorAll("#kpis .kpi[data-click]").forEach(el=>{
    el.onclick=()=>{
      const kind=el.dataset.click;
      let ms,title;
      if(kind==="hp"){ms=CUR_LIST.filter(m=>m.handicap_result);title="让球盈亏明细";}
      else if(kind==="ou"){ms=CUR_LIST.filter(m=>m.ou_result);title="大小球盈亏明细";}
      else{ms=CUR_LIST.filter(m=>m.handicap_result||m.ou_result);title="总盈亏明细";}
      openDetail(title,ms);
    };
  });
}
function renderCharts(list){
  const s=accumulate(list);
  // daily charts (scope filtered by day only)
  const dayList = scope==="all" ? DAYS.map(d=>({d, ms:matchesIn(d)})) : [{d:scope, ms:list}];
  const dayItems=dayList.map(({d,ms})=>{const ss=accumulate(ms);return {label:d.slice(5), value:ss.total, label2:ss.total};});
  vbars(document.getElementById("chartDays"), dayItems);
  const profitItems=dayList.map(({d,ms})=>{const ss=accumulate(ms);return {label:d.slice(5), value:ss.pl_sum, label2:ss.pl_sum};});
  vbars(document.getElementById("chartProfit"), profitItems);
  // win/loss donuts
  const hpParts=["赢","赢半","走水","输半","输"].filter(c=>(s.hp[c]||0)>0).map(c=>({label:c,value:s.hp[c],color:COLORS[c]}));
  const ouParts=["赢","赢半","走水","输半","输"].filter(c=>(s.ou[c]||0)>0).map(c=>({label:c,value:s.ou[c],color:COLORS[c]}));
  donut(document.getElementById("chartHp"), hpParts, s.hp_rate==null?"-":s.hp_rate+"%", "让球胜率");
  donut(document.getElementById("chartOu"), ouParts, s.ou_rate==null?"-":s.ou_rate+"%", "大小球胜率");
  // league profit top10
  const lg={};for(const m of list){(lg[m.league||"未分类"]=lg[m.league||"未分类"]||[]).push(m);}
  const lgRows=Object.keys(lg).map(k=>({label:k, value:accumulate(lg[k]).pl_sum})).sort((a,b)=>Math.abs(b.value)-Math.abs(a.value)).slice(0,10).sort((a,b)=>b.value-a.value);
  hbars(document.getElementById("chartLeague"), lgRows, label=>openDetail("联赛·"+label, CUR_LIST.filter(m=>(m.league||"未分类")===label)));
  // team profit top10
  const tm={};for(const m of list){const mm={...m};(tm[m.home]=tm[m.home]||[]).push(mm);(tm[m.away]=tm[m.away]||[]).push(mm);}
  const tmRows=Object.keys(tm).map(k=>({label:k, value:accumulate(tm[k]).pl_sum})).sort((a,b)=>Math.abs(b.value)-Math.abs(a.value)).slice(0,10).sort((a,b)=>b.value-a.value);
  hbars(document.getElementById("chartTeam"), tmRows, label=>openDetail("球队·"+label, CUR_LIST.filter(m=>m.home===label||m.away===label), label));
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
  const score=m.score?`${esc(m.score)}<span class="half">半 ${esc(m.half||"-")}</span>`:"-";
  const fenxi=m.fenxi_hash?`<a href="https://m.live.qtx.com/fenxi/${esc(m.fenxi_hash)}.html" target="_blank" rel="noopener">分析页 ↗</a>`:"-";
  const open=(m.optional||"").split(";").filter(x=>x.startsWith("status:")).join("; ")||"-";
  return `<tr>
    <td>${esc(m.kickoff||"-")}</td>
    <td>${esc(m.league||m.league_raw||"-")}</td>
    <td class="home">${esc(m.home)}</td>
    <td class="score">${score}</td>
    <td class="away">${esc(m.away)}</td>
    <td>${esc(m.handicap_pick||"-")}</td>
    <td>${esc(m.ou_pick||"-")}</td>
    <td><span class="badge ${statusCls(m.status)}">${esc(m.status)}</span></td>
    <td>${m.handicap_result?`<span class="badge ${resCls(m.handicap_result)}">${esc(m.handicap_result)}</span> <span class="num ${clsNum(hpl)}">${hpl!=null?fmt(hpl):""}</span>`:"-"}</td>
    <td>${m.ou_result?`<span class="badge ${resCls(m.ou_result)}">${esc(m.ou_result)}</span> <span class="num ${clsNum(opl)}">${opl!=null?fmt(opl):""}</span>`:"-"}</td>
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
      <span><b>备注：</b>${esc(m.note||"-")}</span>
      <span><b>创建/更新：</b>${esc(m.created_at||"-")} / ${esc(m.updated_at||"-")}</span>
    </div>
  </tr>`;
}
function renderTable(list){
  const sorted=list.slice().sort((a,b)=>{const va=valOf(a,sortKey),vb=valOf(b,sortKey);if(typeof va==="number"&&typeof vb==="number")return (va-vb)*sortDir;return String(va).localeCompare(String(vb),"zh")*sortDir;});
  const tb=document.querySelector("#matchTable tbody");
  tb.innerHTML=sorted.map((m,i)=>matchRow(m,i)).join("")||'<tr><td colspan="11" class="empty">暂无符合条件的比赛</td></tr>';
  document.querySelectorAll("#matchTable thead th[data-k]").forEach(th=>{const k=th.dataset.k;th.querySelector(".arr").textContent=(k===sortKey?(sortDir===1?"▲":"▼"):"");});
  document.getElementById("tableCount").textContent=`共 ${sorted.length} 场`;
  document.querySelectorAll(".btn-detail").forEach(b=>{b.onclick=()=>{const tr=document.getElementById("detail-"+b.dataset.idx);const show=tr.style.display==="none";tr.style.display=show?"":"none";b.textContent=show?"▾ 详情":"▸ 详情";};});
}
function render(){
  const list=filtered();
  CUR_LIST=list;
  renderTabs();renderKPIs(list);renderCharts(list);renderFilters();renderTable(list);
  document.getElementById("subtitle").textContent=`北京时间自然日 · 数据存于 GitHub 仓库 · 最近更新 ${LEDGER.generated_at||"-"}`;
  document.getElementById("footer").innerHTML=`共 ${DAYS.length} 个比赛日 · ${allMatches().length} 场比赛 · 生成于 ${LEDGER.generated_at||"-"} · 数据源 qtx（球天下）`;
}
document.getElementById("q").addEventListener("input",e=>{q=e.target.value;render();});
document.getElementById("leagueFilter").addEventListener("change",e=>{league=e.target.value;render();});
document.getElementById("statusFilter").addEventListener("change",e=>{status=e.target.value;render();});
function openDetail(title, ms, team){
  const s=accumulate(ms);
  document.getElementById("drawerTitle").textContent=title;
  document.getElementById("drawerKpis").innerHTML=[
    ["场次",s.total],["已结算",s.done],
    ["让球盈亏",fmt(s.pl_h)+" 注",s.pl_h>=0?"g":"r"],
    ["大小球盈亏",fmt(s.pl_o)+" 注",s.pl_o>=0?"g":"r"],
    ["总盈亏",fmt(s.pl_sum)+" 注",s.pl_sum>=0?"g":"r"]
  ].map(k=>`<div class="drawer-kpi"><div class="k">${k[0]}</div><div class="v ${k[2]||""}">${k[1]}</div></div>`).join("");
  const tb=document.querySelector("#drawerTable tbody");
  const sorted=ms.slice().sort((a,b)=>{
    const pa=pl(a.handicap_result,oddsOf(a.handicap_pick,0))||0, qa=pl(a.ou_result,oddsOf(a.ou_pick,0))||0;
    const pb=pl(b.handicap_result,oddsOf(b.handicap_pick,0))||0, qb=pl(b.ou_result,oddsOf(b.ou_pick,0))||0;
    return (pb+qb)-(pa+qa) || String(a.kickoff||"").localeCompare(String(b.kickoff||""),"zh");
  });
  tb.innerHTML=sorted.map(m=>{
    const oh=oddsOf(m.handicap_pick,0),oo=oddsOf(m.ou_pick,0);
    const hpl=pl(m.handicap_result,oh),opl=pl(m.ou_result,oo);
    const tot=hpl!=null&&opl!=null?hpl+opl:(hpl!=null?hpl:(opl!=null?opl:null));
    const hcls=team&&m.home===team?"home hl":"home";
    const acls=team&&m.away===team?"away hl":"away";
    return `<tr>
      <td>${esc(m.day)} ${esc((m.kickoff||"").slice(5,16))}</td>
      <td class="${hcls}">${esc(m.home)}</td>
      <td class="score">${m.score?esc(m.score):"-"}</td>
      <td class="${acls}">${esc(m.away)}</td>
      <td>${esc(m.handicap_pick||"-")}</td>
      <td>${m.handicap_result?`<span class="badge ${resCls(m.handicap_result)}">${esc(m.handicap_result)}</span>`:"-"}</td>
      <td class="num ${clsNum(hpl)}">${hpl!=null?fmt(hpl):"-"}</td>
      <td>${esc(m.ou_pick||"-")}</td>
      <td>${m.ou_result?`<span class="badge ${resCls(m.ou_result)}">${esc(m.ou_result)}</span>`:"-"}</td>
      <td class="num ${clsNum(opl)}">${opl!=null?fmt(opl):"-"}</td>
      <td class="num ${clsNum(tot)}">${tot!=null?fmt(tot):"-"}</td>
      <td><span class="badge ${statusCls(m.status)}">${esc(m.status)}</span></td>
    </tr>`;
  }).join("")||'<tr><td colspan="12" class="empty">暂无明细</td></tr>';
  document.getElementById("drawer").classList.add("open");
}
function closeDrawer(){document.getElementById("drawer").classList.remove("open");}
document.getElementById("drawerClose").onclick=closeDrawer;
document.getElementById("drawer").addEventListener("click",e=>{if(e.target.id==="drawer")closeDrawer();});
document.addEventListener("keydown",e=>{if(e.key==="Escape")closeDrawer();});
document.querySelectorAll("#matchTable thead th[data-k]").forEach(th=>{th.onclick=()=>{const k=th.dataset.k;if(sortKey===k){sortDir*=-1;}else{sortKey=k;sortDir=1;}render();};});
render();
</script>
</body>
</html>
"""
