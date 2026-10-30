"""주소록 CSV로 A4 라벨지(예: 2열×8행 = 16칸)에 맞춘 '우편 라벨 인쇄용 HTML'을 만드는 스크립트.

생각의 흐름:
  1) 고지서·선물·안내문 발송 때 라벨지에 주소를 한 장씩 붙여 넣는 일을 줄입니다.
  2) 워드 '편지 병합' 대신, 브라우저에서 열어 바로 인쇄할 수 있는 HTML을 만듭니다.
     CSS 의 mm 단위와 @page 로 A4 크기·여백을 고정하고, 칸 크기는 옵션으로 받습니다.
  3) 라벨지마다 칸 수·여백이 달라서 --cols, --rows, --top, --left, --gap 옵션으로 맞춥니다.
     (처음엔 일반 종이에 인쇄해 라벨지와 겹쳐 보고 조정하는 것이 안전합니다.)
  4) 이미 몇 칸 쓴 라벨지를 다시 쓸 수 있게 --skip N(앞에서 N칸 비우기)을 둡니다.
  5) 이름·주소에 들어 있는 < > & 같은 글자는 html.escape 로 바꿔서 화면이 깨지지 않게 합니다.
"""
import argparse
import csv
import html


def main():
    p = argparse.ArgumentParser(description="주소 라벨 인쇄용 HTML 만들기")
    p.add_argument("input", help="CSV: 우편번호,주소,상세주소,이름[,호칭]")
    p.add_argument("--cols", type=int, default=2)
    p.add_argument("--rows", type=int, default=8)
    p.add_argument("--top", type=float, default=10.0, help="위 여백 mm")
    p.add_argument("--left", type=float, default=4.0, help="왼쪽 여백 mm")
    p.add_argument("--gap", type=float, default=2.0, help="칸 사이 가로 간격 mm")
    p.add_argument("--skip", type=int, default=0, help="첫 장 앞에서 비울 칸 수")
    p.add_argument("--honorific", default="님", help="호칭 열이 없을 때 붙일 말")
    p.add_argument("-o", "--output", default="labels.out.html")
    a = p.parse_args()

    rows = list(csv.DictReader(open(a.input, encoding="utf-8-sig")))
    per_page = a.cols * a.rows
    w = (210 - a.left * 2 - a.gap * (a.cols - 1)) / a.cols
    h = (297 - a.top * 2) / a.rows

    cells = [""] * a.skip
    for r in rows:
        e = {k: html.escape((v or "").strip()) for k, v in r.items()}
        hon = e.get("호칭") or a.honorific
        cells.append(f'<div class="zip">({e.get("우편번호", "")})</div>'
                     f'<div class="addr">{e.get("주소", "")}<br>{e.get("상세주소", "")}</div>'
                     f'<div class="name">{e.get("이름", "")} <small>{hon}</small></div>')
    pages = [cells[i:i + per_page] for i in range(0, len(cells), per_page)] or [[]]

    body = []
    for pg in pages:
        pg = pg + [""] * (per_page - len(pg))
        body.append('<section class="page">' + "".join(f'<div class="cell">{c}</div>' for c in pg) + "</section>")
    doc = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>주소 라벨</title>
<style>
@page {{ size: A4; margin: 0; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; font-family: "Malgun Gothic", "Apple SD Gothic Neo", sans-serif; background: #fff; color: #000; }}
.page {{ width: 210mm; height: 297mm; padding: {a.top}mm {a.left}mm; display: grid;
  grid-template-columns: repeat({a.cols}, {w:.2f}mm); grid-auto-rows: {h:.2f}mm; column-gap: {a.gap}mm;
  page-break-after: always; }}
.cell {{ padding: 4mm 5mm; overflow: hidden; font-size: 10.5pt; line-height: 1.35; outline: 0.2mm dashed #ccc; }}
.zip {{ font-size: 9pt; }} .addr {{ margin: 1mm 0; }} .name {{ font-size: 12pt; font-weight: bold; text-align: right; }}
@media print {{ .cell {{ outline: none; }} .hint {{ display: none; }} }}
.hint {{ position: fixed; top: 4px; right: 8px; font-size: 12px; color: #c00; }}
</style></head><body><div class="hint">점선은 화면에만 보입니다. 인쇄 배율 100%(실제 크기)로 인쇄하세요.</div>
{''.join(body)}</body></html>"""
    with open(a.output, "w", encoding="utf-8") as f:
        f.write(doc)
    print(f"주소 {len(rows)}건 / 빈칸 {a.skip} / 라벨 {a.cols}×{a.rows} ({w:.1f}×{h:.1f}mm) / {len(pages)}장 → {a.output}")


if __name__ == "__main__":
    main()
