"""영업 실적에 '구간별 누진' 또는 '구간 일괄' 요율을 적용해 인센티브(수수료)를 계산하는 스크립트.

생각의 흐름:
  1) 인센티브 규정은 보통 "0~1천만 원 2%, 1천만~3천만 원 3%, 3천만 원 초과 5%" 같은 구간표입니다.
  2) 같은 구간표라도 계산법이 두 가지라 자주 헷갈립니다.
       - 누진(progressive): 구간마다 그 구간에 해당하는 금액에만 그 요율을 곱해 더합니다(소득세 방식).
       - 일괄(flat): 실적 전체가 속한 '마지막 구간'의 요율을 실적 전체에 곱합니다.
     --mode 로 고르게 하고, 결과표에 구간별 내역을 함께 적어 검증하기 쉽게 합니다.
  3) 구간표는 CSV(하한,요율%)로 받습니다. 하한 오름차순으로 정렬해서 씁니다.
  4) 원 단위 미만은 버림(기본) / 반올림을 고를 수 있게 합니다.
"""
import argparse
import csv
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
from pathlib import Path


def to_dec(s):
    """'12,345,000' 같은 문자열을 Decimal로 바꿉니다."""
    return Decimal(str(s).replace(",", "").strip() or "0")


def load_tiers(path):
    rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
    tiers = sorted((to_dec(r["하한"]), to_dec(r["요율%"]) / 100) for r in rows)
    if not tiers or tiers[0][0] != 0:
        raise SystemExit("[오류] 구간표의 첫 하한은 0이어야 합니다")
    return tiers


def calc(amount, tiers, mode):
    """(인센티브, 내역 문자열)을 돌려줍니다."""
    if amount <= 0:
        return Decimal(0), "실적 없음"
    if mode == "flat":
        rate = [r for low, r in tiers if amount > low or low == 0][-1]
        return amount * rate, f"전체 {amount:,}×{(rate*100).normalize():f}%"
    total, parts = Decimal(0), []
    for i, (low, rate) in enumerate(tiers):
        high = tiers[i + 1][0] if i + 1 < len(tiers) else None
        if amount <= low:
            break
        part = (min(amount, high) if high is not None else amount) - low
        total += part * rate
        parts.append(f"{part:,}×{(rate*100).normalize():f}%")
    return total, " + ".join(parts)


def main():
    p = argparse.ArgumentParser(description="구간별 인센티브 계산")
    p.add_argument("sales_csv", help="실적 CSV (담당자, 실적 열)")
    p.add_argument("tiers_csv", help="구간표 CSV (하한, 요율%)")
    p.add_argument("--mode", choices=["progressive", "flat"], default="progressive",
                   help="progressive=누진(기본), flat=도달 구간 요율 일괄")
    p.add_argument("--name-col", default="담당자")
    p.add_argument("--amount-col", default="실적")
    p.add_argument("--round", choices=["down", "half_up"], default="down", help="원 미만 처리")
    p.add_argument("-o", "--output", default="commission.out.csv")
    a = p.parse_args()

    tiers = load_tiers(a.tiers_csv)
    rnd = ROUND_DOWN if a.round == "down" else ROUND_HALF_UP
    out, grand = [], Decimal(0)
    for r in csv.DictReader(open(a.sales_csv, encoding="utf-8-sig")):
        amt = to_dec(r[a.amount_col])
        pay, detail = calc(amt, tiers, a.mode)
        pay = pay.quantize(Decimal("1"), rounding=rnd)
        grand += pay
        eff = (pay / amt * 100).quantize(Decimal("0.01")) if amt > 0 else Decimal(0)
        out.append({"담당자": r[a.name_col], "실적": f"{amt:f}", "인센티브": f"{pay:f}",
                    "실효요율%": f"{eff:f}", "계산내역": detail})
    with open(a.output, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()) if out else ["담당자"])
        w.writeheader()
        w.writerows(out)
    print(f"방식: {'누진' if a.mode == 'progressive' else '일괄'} / {len(out)}명 / 합계 {grand:,}원 → {a.output}")
    for r in out:
        print(f"  {r['담당자']}: 실적 {to_dec(r['실적']):,} → {to_dec(r['인센티브']):,}원 ({r['계산내역']})")


if __name__ == "__main__":
    main()
