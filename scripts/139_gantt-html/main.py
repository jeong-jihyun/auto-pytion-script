"""작업 일정 CSV로 브라우저에서 보는 간트 차트(HTML 한 장)를 만드는 스크립트.

생각의 흐름:
  1) 프로젝트 주간 보고 때 일정표를 엑셀에서 색칠하며 그리는 데 시간이 많이 듭니다.
  2) 작업·담당·시작일·종료일·진척률만 CSV로 적으면, 날짜 칸에 막대를 그린 HTML 표를 만듭니다.
     외부 라이브러리·인터넷 없이 열리도록 HTML과 CSS만 씁니다(메일 첨부·사내망에서도 열림).
  3) 보기 좋게 하려고
       - 막대를 작업 전체 길이 기준으로 진척률만큼 앞에서부터 진하게 칠하고
       - 기준일(--today) 세로선을 긋고
       - 기준일이 지났는데 진척률 100% 미만인 작업은 '지연'으로 빨갛게 표시합니다.
       - 주말 칸은 옅은 회색
  4) 기간이 길면 하루 한 칸이 너무 좁아지므로 --unit week 로 주 단위 칸도 지원합니다.
  5) 글자는 html.escape 로 처리해 작업명에 <, & 가 있어도 깨지지 않게 합니다.
"""
import argparse
import csv
import html
from datetime import date, datetime, timedelta
from pathlib import Path


def d(s):
    return datetime.strptime(s.strip(), "%Y-%m-%d").date()


def main():
    p = argparse.ArgumentParser(description="일정 CSV → 간트 차트 HTML")
    p.add_argument("tasks", type=Path, help="CSV(작업,담당,시작일,종료일,진척률)")
    p.add_argument("--title", default="프로젝트 일정")
    p.add_argument("--today", default="", help="기준일 YYYY-MM-DD(기본: 오늘)")
    p.add_argument("--unit", choices=["day", "week"], default="day", help="칸 단위(기본 day)")
    p.add_argument("-o", "--output", type=Path, default=Path("output/gantt.html"))
    a = p.parse_args()

    today = d(a.today) if a.today else date.today()
    tasks = []
    with a.tasks.open(newline="", encoding="utf-8-sig") as fp:
        for i, r in enumerate(csv.DictReader(fp), start=2):
            s, e = d(r["시작일"]), d(r["종료일"])
            if e < s:
                raise SystemExit(f"[오류] {i}행 '{r['작업']}': 종료일이 시작일보다 빠릅니다")
            prog = float((r.get("진척률") or "0").replace("%", "").strip() or 0)
            tasks.append({"name": r["작업"].strip(), "who": (r.get("담당") or "").strip(),
                          "s": s, "e": e, "prog": max(0.0, min(100.0, prog))})
    if not tasks:
        raise SystemExit("[오류] 작업이 없습니다")

    lo = min(t["s"] for t in tasks)
    hi = max(t["e"] for t in tasks)
    if a.unit == "week":
        lo -= timedelta(days=lo.weekday())          # 월요일부터 시작
        cells = []
        c = lo
        while c <= hi:
            cells.append((c, c + timedelta(days=6)))
            c += timedelta(days=7)
    else:
        cells = [(lo + timedelta(days=k),) * 2 for k in range((hi - lo).days + 1)]

    def head_label(c):
        return f"{c[0].month}/{c[0].day}" + ("주" if a.unit == "week" else "")

    rows_html = []
    late = 0
    for t in tasks:
        is_late = today > t["e"] and t["prog"] < 100
        late += is_late
        tds = []
        for c in cells:
            inside = c[0] <= t["e"] and c[1] >= t["s"]
            cls = []
            if a.unit == "day" and c[0].weekday() >= 5:
                cls.append("wk")
            if c[0] <= today <= c[1]:
                cls.append("today")
            bar = ""
            if inside:
                # 진척률을 '작업 전체 길이' 기준으로 칠합니다.
                # 예) 10일짜리 작업이 40%면 앞 4일 칸은 진하게, 나머지는 옅게
                total = (t["e"] - t["s"]).days + 1
                done_upto = total * t["prog"] / 100           # 시작일부터 며칠째까지 끝났나
                cs, ce = max(c[0], t["s"]), min(c[1], t["e"])  # 이 칸과 작업이 겹치는 날들
                span = (ce - cs).days + 1
                frac = max(0.0, min(1.0, (done_upto - (cs - t["s"]).days) / span))
                bar = (f'<div class="bar{" late" if is_late else ""}">'
                       f'<div class="done" style="width:{frac * 100:.0f}%"></div></div>')
            tds.append(f'<td class="{" ".join(cls)}">{bar}</td>')
        status = "지연" if is_late else ("완료" if t["prog"] >= 100 else "진행")
        rows_html.append(
            f'<tr><th class="name">{html.escape(t["name"])}</th><td class="who">{html.escape(t["who"])}</td>'
            f'<td class="pct">{t["prog"]:.0f}%</td><td class="st {status}">{status}</td>{"".join(tds)}</tr>')

    head = "".join(f'<th class="d">{head_label(c)}</th>' for c in cells)
    page = f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><title>{html.escape(a.title)}</title>
<style>
body{{font-family:sans-serif;margin:16px;color:#222}}
table{{border-collapse:collapse;font-size:12px}}
th,td{{border:1px solid #ddd;padding:2px 4px;white-space:nowrap}}
th.d{{font-weight:normal;color:#555;min-width:26px}}
th.name{{text-align:left;background:#f7f7f7}}
td.wk{{background:#f2f2f2}} td.today{{border-left:2px solid #e33}}
.bar{{background:#bcd4f5;height:12px;border-radius:3px;overflow:hidden}}
.bar.late{{background:#f5b5b5}} .done{{background:#3874cb;height:100%}} .bar.late .done{{background:#d23}}
.st.지연{{color:#d23;font-weight:bold}} .st.완료{{color:#2a7}}
</style></head><body>
<h2>{html.escape(a.title)}</h2>
<p>기간 {lo} ~ {hi} · 작업 {len(tasks)}개 · 기준일 {today} · 지연 {late}개</p>
<table><tr><th>작업</th><th>담당</th><th>진척</th><th>상태</th>{head}</tr>
{chr(10).join(rows_html)}
</table></body></html>
"""
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(page, encoding="utf-8")
    print(f"작업 {len(tasks)}개, 기간 {lo}~{hi}, 칸 {len(cells)}개({a.unit}), 기준일 {today} 지연 {late}개")
    print(f"저장: {a.output}")


if __name__ == "__main__":
    main()
