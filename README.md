# 足球每日台账（Football Daily Ledger）

每天按**北京时间自然日**扫描一轮足球比赛（让球盘 + 大小球），次日回填赛果并结算，
数据存入本仓库，展示页面由 **GitHub Pages** 自动发布。

## 设计方案

- **数据源**：qtx（球天下）移动版，无需登录。
  - 赛程/盘口：`https://m.live.qtx.com/schedule?date=YYYYMMDD`
  - 完场赛果：`https://m.live.qtx.com/over?date=YYYYMMDD`
  - 反爬：qtx 会返回“客户端环境检测” JS 挑战（MD5 cookie + 倒计时）；已实现 urllib 快速路径 + **Playwright 真实浏览器兜底**（源码 `qtx_source.py`）。
  - CDN 缓存不稳定，已实现多 URL 变体+按 qtx 比赛 ID 去重合并（`fetch_schedule_robust` / `fetch_results_robust`）。
- **存储**：`data/YYYY-MM-DD.json`，每场比赛保存全量信息（比赛ID、赛事、开球时间、主客队、盘口与水位、状态、比分、结算结论、备注、来源等）。
- **流水线**（Windows 计划任务 `FootballLedgerDaily`，每天 09:30）：
  1. `settle` 结算近 5 天（默认窗口，可用 `FOOTBALL_SETTLE_WINDOW_DAYS` 调整）所有未结算行：按 qtx 比赛ID 匹配，查不到且已开球 → 待赛果，次日继续重试
  2. `scan` 扫描今天（按 `日期|主队|客队` 幂等去重，让球和大小球都未开盘的比赛跳过）
  3. `build` 生成 `index.html`
  4. `git commit && git push` → GitHub Pages 自动更新
- **展示**（飞书 Dashboard 风格）：`index.html` 自包含单页，顶部 KPI 大数字卡片 + SVG 图表
  （每日场次、每日盈亏、让球/大小球战绩环形图、联赛盈利 TOP10、球队盈利 TOP10），
  仅具体赛事列表用表格（可切换日期/搜索/筛选/排序/展开详情）。
- **赛事字典**：`dictionary/league_dictionary.supplement.json`，扫描时自动登记新赛事（标准名=原始名，标记“自动登记-待复核”），随数据一起提交；人工可后续把标准名改好。

## 命令

```powershell
python ledger_daily.py doctor        # 本地就绪检查（存储、数据源、git）
python ledger_daily.py dictionary    # 查看赛事字典状态
python ledger_daily.py scan   --date 2026-08-07   # 扫描并冻结某天
python ledger_daily.py settle --date 2026-08-07   # 结算某天
python ledger_daily.py rows    --date 2026-08-07   # 查看某天行
python ledger_daily.py build                        # 生成站点
python ledger_daily.py open                         # 本地浏览器打开
python run_daily.ps1                                # 完整流水线（结算+扫描+构建+推送）
```

## 站点

- 在线地址：<https://sqy098.github.io/football-daily-ledger/>
- 本地地址：`index.html`（构建后直接双击打开即可）

## 结算规则

- 让球：始终按**主队**方向结算冻结时的让球线。
- 大小球：始终按**大球**方向结算冻结时的大小球线。
- 结果：赢 / 赢半 / 走水 / 输半 / 输。
- 盈亏：按冻结时水位计算，1 注为本金 1。

## 已知限制

- 某天扫描完全丢失（如 2026-08-09 qtx 反爬故障）时，既不可能完全回补：历史 `schedule` 页只返回当天数据，`over` 页的盘口是收盘盘口，用它回填会污染统计，因此不自动回补。结算窗口会避免同类问题再次发生在结算环节。

## 目录

- `ledger_daily.py` — 主流程（doctor/scan/settle/rows/build/dictionary）
- `qtx_source.py` — qtx 数据抓取与解析、反爬兑底、赛事字典叠加层
- `settle_markets.py` — 让球/大小球结算（本地化）
- `build_site.py` — GitHub Pages 站点生成（Dashboard 风格）
- `run_daily.ps1` — 每日计划任务入口
- `data/` — 每日比赛数据（提交）
- `dictionary/` — 可写赛事字典叠加层（提交）
- `legacy-feishu/` — 旧的飞书版脚本（已停用，不入库）
