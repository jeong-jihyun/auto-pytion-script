"""구간별 수수료 계산·정산서 스크립트.

거래 CSV(거래일, 고객, 금액)와 수수료 규칙(JSON)으로 거래마다 수수료를 계산하고,
고객별 합계 정산서를 만듭니다.

규칙(JSON) 예:
  {"구간": [{"까지": 1000000, "요율": 0.0015}, {"까지": null, "요율": 0.001}],
   "최소수수료": 100, "원단위": "내림"}
  - '까지' 이하의 금액이면 그 구간 요율을 '거래 금액 전체'에 적용합니다. null 은 끝없음.
  - 원단위: 내림 / 반올림 / 올림 (소수점 이하 처리)
금액은 소수 오차를 피하려고 Decimal 로 계산합니다.
"""
import argparse
import csv
import json
import math
from collections import defaultdict
from decimal import Decimal, ROUND_FLOOR, ROUND_HALF_UP, ROUND_CEILING
from pathlib import Path

ROUND = {"내림": ROUND_FLOOR, "반올림": ROUND_HALF_UP, "올림": ROUND_CEILING}


def calc_fee(amount, rule):
    """금액 하나의 수수료(정수 원)를 계산합니다."""
    rate = None
    for band in rule["구간"]:
        limit = band["까지"]
        if limit is None or amount <= Decimal(str(limit)):
            rate = Decimal(str(band["요율"]))
            break
    if rate is None:
        raise ValueError("규칙에 맞는 구간이 없습니다(마지막 구간의 '까지'는 null 로 하세요)")
    fee = (amount * rate).quantize(Decimal("1"), rounding=ROUND[rule.get("원단위", "내림")])
    return max(fee, Decimal(str(rule.get("최소수수료", 0))))


def main():
    p = argparse.ArgumentParser(description="구간별 수수료 계산")
    p.add_argument("trades", type=Path, help="거래 CSV (열: 거래일,고객,금액)")
    p.add_argument("rules", type=Path, help="수수료 규칙 JSON")
    p.add_argument("-o", "--outdir", type=Path, default=Path("output"))
    a = p.parse_args()

    rule = json.loads(a.rules.read_text(encoding="utf-8"))
    detail, total = [], defaultdict(lambda: [0, Decimal(0), Decimal(0)])
    with a.trades.open(newline="", encoding="utf-8-sig") as fp:
        for n, row in enumerate(csv.DictReader(fp), start=2):
            try:
                amt = Decimal(row["금액"].replace(",", "").strip())
            except Exception:
                print(f"[건너뜀] {n}번째 줄 금액을 읽을 수 없음: {row.get('금액')!r}")
                continue
            fee = calc_fee(amt, rule)
            detail.append([row["거래일"], row["고객"], amt, fee, amt - fee])
            t = total[row["고객"]]
            t[0] += 1
            t[1] += amt
            t[2] += fee

    a.outdir.mkdir(parents=True, exist_ok=True)
    with (a.outdir / "fee_detail.csv").open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["거래일", "고객", "금액", "수수료", "정산액"])
        w.writerows(detail)
    with (a.outdir / "fee_summary.csv").open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["고객", "건수", "금액합계", "수수료합계", "정산액합계"])
        for cust, (cnt, amt, fee) in sorted(total.items()):
            w.writerow([cust, cnt, amt, fee, amt - fee])
    print(f"거래 {len(detail)}건 계산 -> {a.outdir}/fee_detail.csv, fee_summary.csv")
    for cust, (cnt, amt, fee) in sorted(total.items()):
        print(f"  {cust}: {cnt}건, 금액 {amt:,}, 수수료 {fee:,}")


if __name__ == "__main__":
    main()
