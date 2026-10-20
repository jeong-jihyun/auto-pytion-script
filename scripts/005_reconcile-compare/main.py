"""정산/대사(데이터 비교) 스크립트.

두 CSV(예: 우리 시스템 vs 상대 기관)를 '키 열'로 맞춰 비교합니다.
- 한쪽에만 있는 건
- 양쪽에 있지만 금액이 다른 건
- 일치 건수
결과를 output 폴더에 CSV로 저장합니다. 금액은 Decimal로 비교해 소수점 오차를 피합니다.
"""
import argparse
import csv
from decimal import Decimal
from pathlib import Path


def 읽기(path, key, amt):
    d = {}
    with path.open(newline="", encoding="utf-8-sig") as fp:
        for r in csv.DictReader(fp):
            d[r[key]] = Decimal(r[amt].replace(",", ""))
    return d


def 저장(path, rows, header):
    with path.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(header)
        w.writerows(rows)


def main():
    p = argparse.ArgumentParser(description="두 CSV 대사")
    p.add_argument("left", type=Path, help="기준 파일(우리)")
    p.add_argument("right", type=Path, help="비교 파일(상대)")
    p.add_argument("--key", default="거래번호")
    p.add_argument("--amount", default="금액")
    p.add_argument("-o", "--output", type=Path, default=Path("output"))
    a = p.parse_args()
    L, R = 읽기(a.left, a.key, a.amount), 읽기(a.right, a.key, a.amount)
    a.output.mkdir(parents=True, exist_ok=True)
    only_l = [(k, L[k]) for k in sorted(L.keys() - R.keys())]
    only_r = [(k, R[k]) for k in sorted(R.keys() - L.keys())]
    diff = [(k, L[k], R[k], L[k] - R[k]) for k in sorted(L.keys() & R.keys()) if L[k] != R[k]]
    ok = len(L.keys() & R.keys()) - len(diff)
    저장(a.output / "only_left.csv", only_l, [a.key, a.amount])
    저장(a.output / "only_right.csv", only_r, [a.key, a.amount])
    저장(a.output / "amount_diff.csv", diff, [a.key, "left", "right", "차액"])
    print(f"일치 {ok}건 / 금액다름 {len(diff)}건 / 왼쪽만 {len(only_l)}건 / 오른쪽만 {len(only_r)}건")


if __name__ == "__main__":
    main()
