"""CSV를 엑셀 '피벗 테이블'처럼 교차표로 바꾸는 스크립트.

행 기준 열(예: 지점)과 열 기준 열(예: 월)을 정하면, 칸마다 합계·건수·평균을 계산하고
맨 오른쪽에 '합계', 맨 아래에 '합계' 줄을 붙여 줍니다.
"""
import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path


def to_num(text):
    """'1,234' 같은 글자를 숫자로 바꿉니다. 안 되면 None."""
    try:
        return float(str(text).replace(",", "").strip())
    except ValueError:
        return None


def fmt(x):
    """정수처럼 떨어지면 정수로, 아니면 소수 둘째 자리까지."""
    return str(int(x)) if abs(x - round(x)) < 1e-9 else f"{x:.2f}"


def main():
    p = argparse.ArgumentParser(description="CSV 피벗(교차표) 만들기")
    p.add_argument("input", type=Path)
    p.add_argument("--rows", required=True, help="행으로 쓸 열 이름 (예: 지점)")
    p.add_argument("--cols", required=True, help="열로 쓸 열 이름 (예: 월)")
    p.add_argument("--value", help="계산할 숫자 열 (count 일 때는 생략 가능)")
    p.add_argument("--agg", choices=["sum", "count", "avg"], default="sum")
    p.add_argument("-o", "--output", type=Path, default=Path("output/pivot.csv"))
    a = p.parse_args()
    if a.agg != "count" and not a.value:
        print("[오류] sum/avg 는 --value 가 필요합니다.")
        sys.exit(1)

    cells = defaultdict(list)          # (행값, 열값) -> 숫자 목록
    row_keys, col_keys, skipped = [], [], 0
    with a.input.open(newline="", encoding="utf-8-sig") as fp:
        r = csv.DictReader(fp)
        need = [a.rows, a.cols] + ([a.value] if a.value else [])
        for n in need:
            if n not in (r.fieldnames or []):
                print(f"[오류] 없는 열: {n} (있는 열: {r.fieldnames})")
                sys.exit(1)
        for row in r:
            rk, ck = row[a.rows], row[a.cols]
            if rk not in row_keys:
                row_keys.append(rk)
            if ck not in col_keys:
                col_keys.append(ck)
            if a.agg == "count":
                cells[(rk, ck)].append(1.0)
                continue
            v = to_num(row[a.value])
            if v is None:
                skipped += 1           # 숫자가 아닌 칸은 건너뜀
                continue
            cells[(rk, ck)].append(v)
    row_keys.sort()
    col_keys.sort()

    def calc(values):
        if not values:
            return None
        if a.agg == "avg":
            return sum(values) / len(values)
        return sum(values) if a.agg == "sum" else len(values)

    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow([a.rows] + col_keys + ["합계"])
        for rk in row_keys:
            line, allv = [rk], []
            for ck in col_keys:
                vs = cells.get((rk, ck), [])
                allv += vs
                c = calc(vs)
                line.append("" if c is None else fmt(c))
            line.append(fmt(calc(allv)) if allv else "")
            w.writerow(line)
        last, grand = ["합계"], []
        for ck in col_keys:
            vs = [v for rk in row_keys for v in cells.get((rk, ck), [])]
            grand += vs
            last.append(fmt(calc(vs)) if vs else "")
        last.append(fmt(calc(grand)) if grand else "")
        w.writerow(last)
    print(f"[완료] 행 {len(row_keys)}개 x 열 {len(col_keys)}개 ({a.agg}) -> {a.output}")
    if skipped:
        print(f"[알림] 숫자가 아니라서 건너뛴 칸 {skipped}개")


if __name__ == "__main__":
    main()
