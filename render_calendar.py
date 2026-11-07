#!/usr/bin/env python3
"""Render today's screensaver calendar PNG (1264x1680, grayscale) for Kindle Oasis 3.

Layout: big day number, weekday, lunar date, current weather (Markham, ON),
month grid with today highlighted, today's todo list (from todos.json, only
shown when the file's date is today), 3-day forecast. Weather from Open-Meteo
(free, no key). Lunar conversion uses the bundled lunar_table.json
(years 2025-2033, verified against the `lunardate` package).
Output: calendar.png in this script's directory.
"""
import json
import os
import sys
import urllib.request
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
TZ = ZoneInfo("America/Toronto")
W, H = 1264, 1680
LAT, LON = 43.90, -79.27  # Markham, ON

WMO = {0: "晴", 1: "多云", 2: "多云", 3: "阴", 45: "雾", 48: "雾",
       51: "毛毛雨", 53: "毛毛雨", 55: "毛毛雨", 56: "冻毛毛雨", 57: "冻毛毛雨",
       61: "小雨", 63: "中雨", 65: "大雨", 66: "冻雨", 67: "冻雨",
       71: "小雪", 73: "中雪", 75: "大雪", 77: "雪粒",
       80: "阵雨", 81: "阵雨", 82: "暴雨", 85: "阵雪", 86: "阵雪",
       95: "雷阵雨", 96: "冰雹", 99: "冰雹"}
LUNAR_MONTHS = ["正", "二", "三", "四", "五", "六", "七", "八", "九", "十", "冬", "腊"]
WEEKDAYS = ["一", "二", "三", "四", "五", "六", "日"]  # Monday-first


def lunar_day_str(d):
    if d <= 10:
        return "初" + "一二三四五六七八九十"[d - 1]
    if d < 20:
        return "十" + "一二三四五六七八九"[d - 11] if d > 10 else "十"
    if d == 20:
        return "二十"
    if d < 30:
        return "廿" + "一二三四五六七八九"[d - 21] if d > 20 else "廿"
    return "三十"


def solar_to_lunar(solar: date, table: dict):
    """Return (lunar_month, is_leap, lunar_day) using the compact table."""
    for ly in sorted(int(y) for y in table):
        info = table[str(ly)]
        ny = date.fromisoformat(info[0])
        leap = info[1]
        lengths = info[2:]
        segs = []  # (month, is_leap)
        for m in range(1, 13):
            segs.append((m, 0))
            if m == leap:
                segs.append((m, 1))
        assert len(segs) == len(lengths), (ly, len(segs), len(lengths))
        total = sum(lengths)
        offset = (solar - ny).days
        if 0 <= offset < total:
            for (m, isl), ln in zip(segs, lengths):
                if offset < ln:
                    return m, isl, offset + 1
                offset -= ln
    return None


def fetch_weather():
    url = ("https://api.open-meteo.com/v1/forecast?latitude=%s&longitude=%s"
           "&current=temperature_2m,weather_code"
           "&daily=weather_code,temperature_2m_max,temperature_2m_min"
           "&timezone=America%%2FToronto&forecast_days=5" % (LAT, LON))
    req = urllib.request.Request(url, headers={"User-Agent": "kindle-calendar/1.0"})
    with urllib.request.urlopen(req, timeout=25) as r:
        data = json.load(r)
    cur_t = round(data["current"]["temperature_2m"])
    cur_c = WMO.get(data["current"]["weather_code"], "")
    days = data["daily"]
    fc = []
    for i in range(1, 4):
        dt = date.fromisoformat(days["time"][i])
        label = {1: "明天", 2: "后天"}.get(i) or ("周" + WEEKDAYS[dt.weekday()])
        fc.append(("%s %d/%d" % (label, dt.month, dt.day),
                   WMO.get(days["weather_code"][i], ""),
                   "%d° ~ %d°" % (round(days["temperature_2m_min"][i]),
                                  round(days["temperature_2m_max"][i]))))
    return cur_t, cur_c, fc


def load_todos(today: date):
    """Read todos.json next to this script. Return up to 4 short items, but
    only when the file's date is today (stale todos are never shown).
    Items are pre-sanitized by the writer: short phrases, no names/amounts."""
    try:
        data = json.load(open(os.path.join(HERE, "todos.json"), encoding="utf-8"))
    except Exception:
        return []
    if data.get("date") != today.isoformat():
        return []
    items = []
    for it in data.get("items", [])[:4]:
        it = str(it).strip()
        if it:
            items.append(it[:24])
    return items


def find_font(bold=False, serif=False):
    import glob
    pats = []
    names = (["NotoSerifCJK"] if serif else ["NotoSansCJK", "NotoSerifCJK"])
    for n in names:
        pats.append("/usr/share/fonts/opentype/noto/%s-%s.ttc" % (n, "Bold" if bold else "Regular"))
        pats.append("/usr/share/fonts/truetype/noto/%s-%s.ttc" % (n, "Bold" if bold else "Regular"))
        pats += glob.glob("/usr/share/fonts/**/%s-%s.*" % (n, "Bold" if bold else "Regular"), recursive=True)
    for p in pats:
        if os.path.exists(p):
            return p
    raise RuntimeError("No CJK font found")


def render(today: date, weather, lunar, todos, out_path):
    img = Image.new("L", (W, H), 255)
    d = ImageDraw.Draw(img)

    def font(size, bold=False, serif=False):
        return ImageFont.truetype(find_font(bold, serif), size)

    def ctext(cx, y, s, fnt, fill=0):
        d.text((cx, y), s, font=fnt, fill=fill, anchor="ma")

    BLACK, GRAY, LGRAY = 0, 110, 190

    y = 56
    ctext(W / 2, y, "%d 年 %d 月" % (today.year, today.month), font(56, bold=True)); y += 78
    ctext(W / 2, y, "星 期 " + WEEKDAYS[today.weekday()], font(42), fill=GRAY); y += 58

    f_big = font(288, bold=True)
    s = str(today.day)
    bb = d.textbbox((0, 0), s, font=f_big)
    d.text((W / 2, y + 6), s, font=f_big, fill=BLACK, anchor="mt")
    y += (bb[3] - bb[1]) + 22

    lm, leap, ld = lunar
    lunar_str = "农历" + ("闰" if leap else "") + LUNAR_MONTHS[lm - 1] + "月" + lunar_day_str(ld)
    ctext(W / 2, y, lunar_str, font(56, serif=True)); y += 72

    if weather:
        cur_t, cur_c, _ = weather
        ctext(W / 2, y, "Markham 现在 %d°C · %s" % (cur_t, cur_c), font(42), fill=GRAY)
    y += 70

    d.line([(90, y), (W - 90, y)], fill=LGRAY, width=3); y += 36

    gx, cw = 82, 157
    for i, lb in enumerate(["日", "一", "二", "三", "四", "五", "六"]):
        ctext(gx + i * cw + cw / 2, y, lb, font(38, bold=True), fill=GRAY)
    y += 50
    chh = 74
    first = date(today.year, today.month, 1)
    start_col = (first.weekday() + 1) % 7  # Sunday-first grid
    import calendar as _cal
    ndays = _cal.monthrange(today.year, today.month)[1]
    cell = 0
    for r in range(6):
        for c in range(7):
            daynum = cell - start_col + 1
            cell += 1
            if not (1 <= daynum <= ndays):
                continue
            x0, y0 = gx + c * cw, y + r * chh
            if daynum == today.day:
                d.rounded_rectangle([x0 + 18, y0 + 8, x0 + cw - 18, y0 + chh - 8], radius=18, fill=BLACK)
                ctext(x0 + cw / 2, y0 + 12, str(daynum), font(50, bold=True), fill=255)
            else:
                ctext(x0 + cw / 2, y0 + 12, str(daynum), font(50),
                      fill=(BLACK if c in (0, 6) else 60))
        if cell - start_col >= ndays:
            used_rows = r + 1
            break
    y += used_rows * chh + 26

    if todos:
        d.line([(90, y), (W - 90, y)], fill=LGRAY, width=3); y += 28
        ctext(W / 2, y, "今 日 待 办", font(38, bold=True), fill=GRAY); y += 52
        for it in todos:
            d.text((118, y), "□ " + it, font=font(40), fill=BLACK, anchor="la")
            y += 52
        y += 4

    d.line([(90, y), (W - 90, y)], fill=LGRAY, width=3); y += 30
    ctext(W / 2, y, "天 气 预 报", font(38, bold=True), fill=GRAY); y += 52

    if weather:
        fc = weather[2]
        colw = (W - 120) // 3
        for i, (t, cond, temp) in enumerate(fc):
            cx = 60 + i * colw + colw / 2
            ctext(cx, y, t, font(38), fill=GRAY)
            ctext(cx, y + 48, cond, font(54, bold=True))
            ctext(cx, y + 112, temp, font(42))
        y += 112 + 46

    if y < H - 84:
        ctext(W / 2, H - 64, "Kindle 屏保日历", font(30), fill=LGRAY)
    img.save(out_path)


def main():
    today = datetime.now(TZ).date()
    table = json.load(open(os.path.join(HERE, "lunar_table.json"), encoding="utf-8"))
    lunar = solar_to_lunar(today, table)
    if lunar is None:
        print("lunar table does not cover", today, file=sys.stderr)
        sys.exit(1)
    weather = None
    try:
        weather = fetch_weather()
    except Exception as e:  # keep rendering without weather
        print("weather fetch failed:", e, file=sys.stderr)
    todos = load_todos(today)
    out = os.path.join(HERE, "calendar.png")
    render(today, weather, lunar, todos, out)
    print("rendered", out, "for", today, "lunar", lunar, "todos", len(todos))


if __name__ == "__main__":
    main()
