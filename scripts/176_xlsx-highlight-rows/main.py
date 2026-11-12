"""CSV를 엑셀(xlsx)로 바꾸면서, 규칙(JSON)에 맞는 행이나 칸에 색을 칠해 주는 스크립트.

생각의 흐름:
  1) 점검 결과를 엑셀로 공유할 때 '금액 1억 이상은 노랑, 상태가 실패면 빨강'처럼 색을 칠하면
     받는 사람이 바로 눈에 띕니다. 매번 조건부 서식을 손으로 거는 건 번거롭습니다.
  2) 규칙 JSON에 [열, 비교(>=, <=, >, <, ==, !=, contains, empty), 값, 색, 범위(row/cell)]를 적습니다.
  3) CSV를 한 줄씩 읽어 엑셀에 쓰고, 숫자처럼 보이는 값은 숫자로 넣어 엑셀에서 합계가 되게 합니다.
  4) 규칙을 위에서부터 검사해 맞으면 색을 칠합니다. 같은 칸에 여러 규칙이 맞으면 뒤 규칙 색이 덮습니다.
  5) 머리글은 굵게·고정(틀 고정), 열 너비는 글자 길이에 맞추고, 규칙별 맞은 건수를 화면에 보여 줍니다.
"""
import argparse
import csv
import json
import os
import re

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

NUM_RE = re.compile(r"^-?\d{1,3}(,\d{3})+(\.\d+)?$|^-?\d+(\.\d+)?$")
COLORS = {"노랑": "FFF2CC", "빨강": "F8CBAD", "초록": "C6EFCE", "파랑": "DDEBF7", "회색": "E7E6E6"}


def to_value(v):
    """숫자처럼 보이면 숫자로. 단 앞자리 0 코드(00123)는 글자로 둡니다."""
    s = v.strip()
    if NUM_RE.match(s) and not (len(s) > 1 and s.startswith("0") and not s.startswith("0.")):
        n = float(s.replace(",", ""))
        return int(n) if n.is_integer() and "." not in s else n
    return v


def match(cell, op, target):
    if op == "empty":
        return str(cell).strip() == ""
    if op == "contains":
        return str(target) in str(cell)
    if op in ("==", "!="):
        eq = str(cell) == str(target) or (isinstance(cell, (int, float)) and _f(target) == cell)
        return eq if op == "==" else not eq
    if not isinstance(cell, (int, float)):
        return False   # 숫자 비교인데 칸이 숫자가 아니면 맞지 않음
    t = _f(target)
    return {">=": cell >= t, "<=": cell <= t, ">": cell > t, "<": cell < t}[op]


def _f(x):
    try:
        return float(str(x).replace(",", ""))
    except ValueError:
        return None


def main():
    ap = argparse.ArgumentParser(description="CSV → xlsx, 규칙에 맞는 행·칸 색칠")
    ap.add_argument("input", help="입력 CSV")
    ap.add_argument("--rules", required=True, help="규칙 JSON 파일")
    ap.add_argument("--sheet", default="데이터")
    ap.add_argument("-o", "--out", default="", help="출력 xlsx (기본: out/<입력이름>.xlsx)")
    args = ap.parse_args()

    with open(args.rules, encoding="utf-8") as f:
        rules = json.load(f)
    with open(args.input, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))
    header, data = rows[0], rows[1:]
    for i, r in enumerate(rules, 1):
        if r["열"] not in header:
            raise SystemExit(f"규칙 {i}: 열 '{r['열']}' 이 CSV에 없습니다. 있는 열: {header}")
        if r["비교"] not in (">=", "<=", ">", "<", "==", "!=", "contains", "empty"):
            raise SystemExit(f"규칙 {i}: 비교 '{r['비교']}' 를 모릅니다")

    wb = Workbook()
    ws = wb.active
    ws.title = args.sheet
    ws.append(header)
    for c in ws[1]:
        c.font = Font(bold=True)
    ws.freeze_panes = "A2"

    hits = [0] * len(rules)
    for row in data:
        values = [to_value(v) for v in row]
        ws.append(values)
        excel_row = ws.max_row
        for c in ws[excel_row]:
            if isinstance(c.value, (int, float)):
                c.number_format = "#,##0" if isinstance(c.value, int) else "#,##0.00"   # 천 단위 쉼표
        for i, r in enumerate(rules):
            col = header.index(r["열"])
            if match(values[col] if col < len(values) else "", r["비교"], r.get("값", "")):
                hits[i] += 1
                fill = PatternFill("solid", fgColor=COLORS.get(r.get("색", "노랑"), r.get("색", "FFF2CC")))
                if r.get("범위", "row") == "row":
                    for c in ws[excel_row]:
                        c.fill = fill
                else:
                    ws.cell(row=excel_row, column=col + 1).fill = fill

    for idx, name in enumerate(header, 1):
        width = max([len(str(name))] + [len(str(r[idx - 1])) for r in data if idx - 1 < len(r)])
        ws.column_dimensions[ws.cell(row=1, column=idx).column_letter].width = min(width * 1.6 + 2, 60)

    out = args.out or os.path.join("out", os.path.splitext(os.path.basename(args.input))[0] + ".xlsx")
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    wb.save(out)
    print(f"{len(data)}행을 엑셀로 저장 → {out}")
    for r, n in zip(rules, hits):
        print(f"  [{r.get('색', '노랑')}/{r.get('범위', 'row')}] {r['열']} {r['비교']} {r.get('값', '')}: {n}건")


if __name__ == "__main__":
    main()
