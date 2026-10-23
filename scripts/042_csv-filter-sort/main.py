"""CSV에서 조건에 맞는 행만 거르고, 원하는 열 기준으로 정렬하는 스크립트.

조건은 --where 로 여러 번 쓸 수 있고, 모두 만족해야(AND) 남습니다.
  형식: "열이름 연산자 값"   연산자: ==  !=  >  >=  <  <=  contains
  예) --where "지점 == 서울" --where "금액 >= 100000"
숫자로 읽을 수 있으면 숫자로, 아니면 글자로 비교합니다.
"""
import argparse
import csv
import re
import sys
from pathlib import Path

OPS = ["contains", "==", "!=", ">=", "<=", ">", "<"]


def to_num(text):
    """'1,200' 같은 글자를 숫자로 바꿉니다. 안 되면 None."""
    try:
        return float(str(text).replace(",", "").strip())
    except ValueError:
        return None


def parse_where(expr):
    """'금액 >= 1000' -> ('금액', '>=', '1000')"""
    for op in OPS:
        m = re.match(rf"^\s*(.+?)\s+{re.escape(op)}\s+(.*?)\s*$", expr)
        if m:
            return m.group(1), op, m.group(2)
    raise ValueError(f"조건 형식이 틀렸습니다: '{expr}'  (예: \"금액 >= 1000\")")


def check(cell, op, value):
    """한 칸이 조건을 만족하는지 검사합니다."""
    if op == "contains":
        return value in cell
    a, b = to_num(cell), to_num(value)
    if a is not None and b is not None:
        left, right = a, b
    else:
        left, right = cell, value
    return {"==": left == right, "!=": left != right, ">": left > right,
            ">=": left >= right, "<": left < right, "<=": left <= right}[op]


def main():
    p = argparse.ArgumentParser(description="CSV 행 거르기·정렬")
    p.add_argument("input", type=Path)
    p.add_argument("-o", "--output", type=Path, default=Path("output/filtered.csv"))
    p.add_argument("--where", action="append", default=[], help='조건 "열 연산자 값" (여러 번 가능)')
    p.add_argument("--sort", help="정렬 기준 열")
    p.add_argument("--desc", action="store_true", help="내림차순")
    a = p.parse_args()

    with a.input.open(newline="", encoding="utf-8-sig") as fp:
        r = csv.DictReader(fp)
        header = r.fieldnames or []
        rows = list(r)
    try:
        conds = [parse_where(w) for w in a.where]
    except ValueError as e:
        print("[오류]", e)
        sys.exit(1)
    for col, _, _ in conds + ([(a.sort, 0, 0)] if a.sort else []):
        if col not in header:
            print(f"[오류] 없는 열: {col}  (있는 열: {header})")
            sys.exit(1)

    kept = [row for row in rows if all(check(row[c], op, v) for c, op, v in conds)]
    if a.sort:
        # 숫자 열이면 숫자 순서로, 아니면 글자 순서로 정렬합니다.
        if all(to_num(x[a.sort]) is not None for x in kept):
            kept.sort(key=lambda x: to_num(x[a.sort]), reverse=a.desc)
        else:
            kept.sort(key=lambda x: x[a.sort], reverse=a.desc)

    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.DictWriter(fp, fieldnames=header)
        w.writeheader()
        w.writerows(kept)
    print(f"전체 {len(rows)}행 중 {len(kept)}행 남김 -> {a.output}")


if __name__ == "__main__":
    main()
