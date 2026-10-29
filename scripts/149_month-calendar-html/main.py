"""일정 CSV를 월간 달력 HTML 한 장으로 만드는 스크립트.

생각의 흐름:
  1) 팀 일정(휴가·마감·배포·점검)은 보통 엑셀 목록으로 관리하지만, 한눈에 보려면 달력 모양이 편합니다.
  2) 표준 라이브러리 calendar 모듈로 해당 달의 주(週) 배열을 만들고, 날짜 칸마다 그날 일정을 넣습니다.
  3) 일정은 '시작일~종료일'이 있으면 그 기간의 모든 날에 표시합니다(휴가처럼 여러 날 일정).
  4) '구분' 열 값마다 색을 자동으로 정해 범례를 붙입니다. 공휴일 파일(날짜,이름)을 주면 빨간 글씨로 표시합니다.
  5) 결과는 외부 파일이 필요 없는 HTML 하나입니다. 브라우저로 열고 인쇄(가로)하면 벽에 붙일 수도 있습니다.
     글자는 html.escape 로 처리해 일정 이름에 < > 가 있어도 깨지지 않게 합니다.
"""
import argparse
import calendar
import csv
import html
from collections import defaultdict
from datetime import date, datetime, timedelta

PALETTE = ["#2563eb", "#16a34a", "#d97706", "#9333ea", "#dc2626", "#0891b2", "#4b5563", "#db2777"]


def to_date(text):
    text = (text or "").strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    return None


def main():
    p = argparse.ArgumentParser(description="일정 CSV → 월간 달력 HTML")
    p.add_argument("input", help="일정 CSV (제목, 시작일, 종료일(선택), 구분(선택))")
    p.add_argument("--month", required=True, help="만들 달 (예: 2026-11)")
    p.add_argument("-o", "--output", default="calendar.out.html")
    p.add_argument("--holidays", help="공휴일 CSV (날짜, 이름)")
    p.add_argument("--title", default="", help="달력 제목")
    p.add_argument("--monday", action="store_true", help="월요일부터 시작 (기본은 일요일 시작)")
    a = p.parse_args()

    try:
        year, month = int(a.month[:4]), int(a.month[5:7])
        first = date(year, month, 1)
    except ValueError:
        raise SystemExit("[오류] --month 형식은 2026-11 처럼 씁니다")
    last = date(year, month, calendar.monthrange(year, month)[1])

    events = defaultdict(list)
    colors = {}
    count, skipped = 0, 0
    with open(a.input, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            start = to_date(row.get("시작일"))
            end = to_date(row.get("종료일")) or start
            if not start or end < start:
                skipped += 1
                continue
            kind = (row.get("구분") or "기타").strip()
            colors.setdefault(kind, PALETTE[len(colors) % len(PALETTE)])
            d = max(start, first)
            hit = False
            while d <= min(end, last):
                events[d].append((row.get("제목", "").strip(), kind))
                d += timedelta(days=1)
                hit = True
            count += hit

    holidays = {}
    if a.holidays:
        with open(a.holidays, encoding="utf-8-sig", newline="") as f:
            for row in csv.reader(f):
                d = to_date(row[0]) if row else None
                if d:
                    holidays[d] = row[1] if len(row) > 1 else "휴일"

    cal = calendar.Calendar(firstweekday=0 if a.monday else 6)
    names = ["월", "화", "수", "목", "금", "토", "일"]
    head = names if a.monday else names[6:] + names[:6]

    cells = []
    for week in cal.monthdatescalendar(year, month):
        tds = []
        for d in week:
            cls = []
            if d.month != month:
                cls.append("other")
            if d.weekday() == 6 or d in holidays:
                cls.append("red")
            elif d.weekday() == 5:
                cls.append("blue")
            items = "".join(
                f'<div class="ev" style="background:{colors[k]}">{html.escape(t)}</div>'
                for t, k in events.get(d, []))
            hol = f'<span class="hol">{html.escape(holidays[d])}</span>' if d in holidays else ""
            tds.append(f'<td class="{" ".join(cls)}"><div class="day">{d.day}{hol}</div>{items}</td>')
        cells.append("<tr>" + "".join(tds) + "</tr>")

    legend = "".join(f'<span class="lg"><i style="background:{c}"></i>{html.escape(k)}</span>' for k, c in colors.items())
    title = html.escape(a.title or f"{year}년 {month}월 일정")
    doc = f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
body{{font-family:'Malgun Gothic','Apple SD Gothic Neo',sans-serif;margin:16px;color:#111;background:#fff}}
h1{{font-size:22px;margin:0 0 8px}}
table{{width:100%;border-collapse:collapse;table-layout:fixed}}
th{{background:#f3f4f6;padding:6px;font-size:13px}}
td{{border:1px solid #d1d5db;vertical-align:top;height:96px;padding:4px;font-size:12px}}
.day{{font-weight:bold;margin-bottom:2px}} .other{{background:#fafafa;color:#9ca3af}}
.red .day{{color:#dc2626}} .blue .day{{color:#2563eb}}
.hol{{font-weight:normal;font-size:11px;margin-left:4px}}
.ev{{color:#fff;border-radius:3px;padding:1px 4px;margin:2px 0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.lg{{margin-right:12px;font-size:13px}} .lg i{{display:inline-block;width:10px;height:10px;margin-right:4px;border-radius:2px}}
@media print{{@page{{size:A4 landscape;margin:10mm}}}}
</style></head><body>
<h1>{title}</h1><p>{legend}</p>
<table><thead><tr>{''.join(f'<th>{h}</th>' for h in head)}</tr></thead><tbody>
{''.join(cells)}
</tbody></table>
</body></html>
"""
    with open(a.output, "w", encoding="utf-8") as f:
        f.write(doc)
    print(f"{year}-{month:02d} 달력: 이 달에 걸친 일정 {count}건, 구분 {len(colors)}종 → {a.output}")
    if skipped:
        print(f"[경고] 날짜를 읽지 못했거나 종료일이 시작일보다 빠른 일정 {skipped}건은 뺐습니다")


if __name__ == "__main__":
    main()
