"""CSV를 보기 좋은 HTML 표 보고서 한 장으로 만드는 스크립트.

브라우저로 열면 바로 보이고, 인쇄해서 PDF로 저장할 수도 있습니다.
- 헤더가 고정되고 줄무늬가 있는 표
- 숫자 열은 오른쪽 정렬 + 천 단위 쉼표
- --sum-cols 로 지정한 열은 맨 아래에 합계 행을 붙입니다
외부 파일(CSS, JS)을 쓰지 않는 단일 HTML 입니다.
"""
import argparse
import csv
import html
from datetime import datetime
from pathlib import Path


def to_num(text):
    try:
        return float(str(text).replace(",", "").strip())
    except ValueError:
        return None


def fmt(n):
    """숫자를 천 단위 쉼표로(정수면 소수점 없이)."""
    return f"{n:,.0f}" if n == int(n) else f"{n:,.2f}"


def main():
    p = argparse.ArgumentParser(description="CSV -> HTML 보고서")
    p.add_argument("input", type=Path)
    p.add_argument("-o", "--output", type=Path, default=Path("output/report.html"))
    p.add_argument("--title", default="보고서", help="보고서 제목")
    p.add_argument("--sum-cols", default="", help="합계를 낼 열(쉼표 구분)")
    a = p.parse_args()

    with a.input.open(newline="", encoding="utf-8-sig") as fp:
        r = csv.reader(fp)
        header = next(r)
        rows = [x for x in r if any(c.strip() for c in x)]
    sum_cols = [c.strip() for c in a.sum_cols.split(",") if c.strip()]
    # 열의 값이 전부 숫자면 숫자 열로 봅니다.
    numeric = [all(to_num(x[i]) is not None for x in rows if i < len(x) and x[i].strip()) for i in range(len(header))]

    def cell(i, v):
        n = to_num(v)
        if numeric[i] and n is not None:
            return f'<td class="num">{fmt(n)}</td>'
        return f"<td>{html.escape(v)}</td>"

    body = "\n".join("<tr>" + "".join(cell(i, v) for i, v in enumerate(x)) + "</tr>" for x in rows)
    foot = ""
    if sum_cols:
        cells = []
        for i, h in enumerate(header):
            if h in sum_cols and numeric[i]:
                total = sum(to_num(x[i]) or 0 for x in rows)
                cells.append(f'<td class="num">{fmt(total)}</td>')
            else:
                cells.append("<td>합계</td>" if i == 0 else "<td></td>")
        foot = "<tfoot><tr>" + "".join(cells) + "</tr></tfoot>"
    head = "".join(f"<th>{html.escape(h)}</th>" for h in header)
    page = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<title>{html.escape(a.title)}</title>
<style>
body{{font-family:sans-serif;margin:24px;color:#222}}
h1{{font-size:20px}} .meta{{color:#666;font-size:12px;margin-bottom:12px}}
table{{border-collapse:collapse;width:100%;font-size:13px}}
th,td{{border:1px solid #ccc;padding:6px 10px}}
th{{background:#2f4f6f;color:#fff;position:sticky;top:0}}
tbody tr:nth-child(even){{background:#f3f6f9}}
td.num{{text-align:right}} tfoot td{{font-weight:bold;background:#e6ecf2}}
</style></head><body>
<h1>{html.escape(a.title)}</h1>
<div class="meta">원본: {html.escape(a.input.name)} · {len(rows)}행 · 만든 시각 {datetime.now():%Y-%m-%d %H:%M}</div>
<table><thead><tr>{head}</tr></thead><tbody>
{body}
</tbody>{foot}</table></body></html>"""
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(page, encoding="utf-8")
    print(f"{len(rows)}행 보고서 저장: {a.output}")


if __name__ == "__main__":
    main()
