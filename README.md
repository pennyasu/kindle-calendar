# kindle-calendar — Kindle 屏保日历（每日自动版）

每天由 GitHub Actions 渲染一张当天的日历图（1264×1680 灰阶 PNG，适配 Kindle Oasis 3），
Kindle 上的 KOReader 小插件 calfetch 每天把新图下载下来、覆盖为屏保图。
图上除了日期、农历与 Markham 天气，还有一栏「今日待办」。

## 数据流

1. `.github/workflows/daily.yml`：每天多伦多时间清晨运行 `render_calendar.py`
   （日期/星期、农历、Markham 实时天气 + 三天预报，天气源 Open-Meteo 免费接口），
   把新 `calendar.png` 提交回仓库。
2. `todos.json`：当天的待办（格式 `{"date": "YYYY-MM-DD", "items": [...]}`，最多显示 4 条）。
   由 Thomas 的助理每天早上脱敏整理后推送到本仓库，推送即触发重新渲染；
   日期不是当天的待办不会显示。**脱敏口径**：只写短句，不含客户姓名、金额、
   案件细节——本仓库是公开的（为了 Kindle 免令牌拉图），凡是写进 todos.json 的内容都视为可公开。
3. Kindle 端 `plugin/calfetch.koplugin`：KOReader 启动/唤醒时检查
   `koreader/calendar.png` 是否为今天，不是就从
   `https://raw.githubusercontent.com/pennyasu/kindle-calendar/main/calendar.png`
   下载覆盖；「工具」菜单里也有「更新屏保日历」可手动触发。
4. 在 KOReader 屏保设置里把屏保图片**一次性**指到 `koreader/calendar.png`，之后全自动。

## 文件

- `render_calendar.py` — 渲染脚本（Pillow + 农历表；农历表覆盖 2025–2033，含闰月，已与 lunardate 抽检零误差）
- `lunar_table.json` — 精简农历表：每年 = [正月初一公历日期， 闰月， 各月天数（按序，闰月紧随其本月）]
- `todos.json` — 当日待办（脱敏短句，见上）
- `calendar.png` — 当日图（由 Actions 每日更新）
- `plugin/calfetch.koplugin/` — Kindle 端抓图插件源码，解压到 `koreader/plugins/` 安装

## 本地自测

```bash
pip install pillow
python3 render_calendar.py   # 生成 calendar.png
```
