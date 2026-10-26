"""사람별 현금 지급액을 권종(5만원권, 1만원권 …)으로 나눠 몇 장씩 필요한지 계산하는 스크립트.

생각의 흐름:
  1) 현금 봉투(경조금·일당·시상금·소액 환급)를 준비할 때 은행에서 권종별로 얼마나 찾을지 알아야 합니다.
  2) 큰 돈부터 나누는 방식(탐욕법)이 원화 권종에서는 가장 적은 장수를 만듭니다.
     예) 87,000원 = 5만원 1장 + 1만원 3장 + 5천원 1장 + 1천원 2장
  3) 사람별 장수를 구한 뒤 권종별로 모두 더하면 '은행에서 찾을 목록'이 됩니다.
  4) 가장 작은 권종으로도 나눌 수 없는 나머지(예: 10원 미만)는 따로 표시합니다.
"""
import argparse
import csv
from pathlib import Path

DEFAULT = [50000, 10000, 5000, 1000, 500, 100, 50, 10]


def split(amount, denoms):
    """금액을 권종별 장수로 나누고 (장수 목록, 나머지)를 돌려줍니다."""
    counts = []
    for d in denoms:
        counts.append(amount // d)
        amount %= d
    return counts, amount


def main():
    p = argparse.ArgumentParser(description="현금 지급 권종 계산")
    p.add_argument("payees", type=Path, help="CSV(이름,금액)")
    p.add_argument("--denoms", help="쓸 권종을 쉼표로, 예: 50000,10000,5000,1000 (동전 제외)")
    p.add_argument("-o", "--output", type=Path, default=Path("output/cash_denomination.csv"))
    a = p.parse_args()

    denoms = sorted((int(x) for x in a.denoms.split(",")), reverse=True) if a.denoms else DEFAULT
    totals, rows, grand = [0] * len(denoms), [], 0
    with a.payees.open(newline="", encoding="utf-8-sig") as fp:
        for r in csv.DictReader(fp):
            amt = int(r["금액"].replace(",", "").strip())
            counts, rest = split(amt, denoms)
            totals = [t + c for t, c in zip(totals, counts)]
            grand += amt
            rows.append([r["이름"], amt] + counts + [rest])

    a.output.parent.mkdir(parents=True, exist_ok=True)
    head = ["이름", "금액"] + [f"{d:,}원" for d in denoms] + ["나눌수없는나머지"]
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(head)
        w.writerows(rows)
        w.writerow(["합계(은행에서 찾을 장수)", grand] + totals + [sum(r[-1] for r in rows)])

    print(f"{len(rows)}명, 총 {grand:,}원 → {a.output}")
    print("은행에서 찾을 목록:")
    for d, t in zip(denoms, totals):
        if t:
            print(f"  {d:>6,}원 × {t}장 = {d * t:,}원")
    rest = sum(r[-1] for r in rows)
    if rest:
        print(f"  ※ 권종으로 나눌 수 없는 나머지 합계 {rest:,}원 (계좌 이체 등으로 처리)")


if __name__ == "__main__":
    main()
