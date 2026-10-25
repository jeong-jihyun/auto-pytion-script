"""총액을 비율대로 나누되, 원 단위로 반올림해도 합계가 딱 맞게 배분하는 스크립트.

생각의 흐름:
  1) 단순히 비율대로 나눠 반올림하면 합계가 1~2원 어긋나는 일이 생깁니다.
  2) 그래서 먼저 각 몫의 '정수 부분'(내림)만 배정합니다.
  3) 남은 금액(총액 - 정수 합)은 소수 부분이 큰 순서대로 1원씩 나눠 줍니다(최대잔여법).
  4) 동점이면 입력 순서가 앞선 쪽이 먼저 받습니다. 항상 같은 결과가 나옵니다.
"""
import argparse
import csv
from decimal import Decimal, ROUND_FLOOR
from pathlib import Path


def allocate(total, weights, unit=Decimal(1)):
    """total 을 weights 비율로 unit 단위로 나눕니다. 합계는 정확히 total."""
    wsum = sum(weights)
    if wsum <= 0:
        raise ValueError("비율 합이 0 이하입니다")
    units = int(total / unit)
    if units * unit != total:
        raise ValueError("총액이 단위의 배수가 아닙니다")
    exact = [Decimal(units) * w / wsum for w in weights]
    base = [int(x.to_integral_value(rounding=ROUND_FLOOR)) for x in exact]
    left = units - sum(base)
    order = sorted(range(len(weights)), key=lambda i: (-(exact[i] - base[i]), i))
    for i in order[:left]:
        base[i] += 1
    return [Decimal(b) * unit for b in base]


def main():
    p = argparse.ArgumentParser(description="최대잔여법 배분")
    p.add_argument("--input", required=True, help="CSV(이름,비율)")
    p.add_argument("--total", required=True, help="나눌 총액(예: 1000000)")
    p.add_argument("--unit", default="1", help="배분 단위(기본 1원)")
    p.add_argument("--out", default="output/배분결과.csv")
    a = p.parse_args()

    with open(a.input, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    weights = [Decimal(r["비율"].replace(",", "")) for r in rows]
    total = Decimal(a.total.replace(",", ""))
    result = allocate(total, weights, Decimal(a.unit))
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["이름", "비율", "배분액"])
        for r, amt in zip(rows, result):
            w.writerow([r["이름"], r["비율"], amt])
            print(f"{r['이름']}: {amt:,}")
    print(f"합계 {sum(result):,} (총액 {total:,}) -> {'일치' if sum(result) == total else '불일치'}")


if __name__ == "__main__":
    main()
