"""외화 채권·채무(외화 예금, 외상매출금, 외상매입금 등)를 기말 환율로 다시 계산해 외화환산손익을 구하는 스크립트.

생각의 흐름:
  1) 달러로 받을 돈 1만 달러를 1,350원일 때 장부에 1,350만 원으로 적었는데 월말 환율이 1,400원이면
     원화로는 1,400만 원 가치가 되어 50만 원 '이익'이 생깁니다. 이것이 외화환산이익입니다.
  2) 반대로 갚을 돈(채무)은 환율이 오르면 더 많이 갚아야 하므로 '손실'입니다.
     그래서 '구분'이 자산이면 (기말평가액 - 장부금액), 부채면 (장부금액 - 기말평가액) 이 손익입니다.
  3) 기말 환율은 통화별 CSV(통화,환율)로 받고, JPY처럼 100단위로 고시되는 통화는 '단위' 열(100)로 나눕니다.
  4) 원 미만은 반올림(ROUND_HALF_UP)하고, 계정·통화별 합계와 이익·손실 합계를 냅니다.
  5) 결과는 분개 참고용 CSV입니다. 회계 처리 기준은 회사 규정을 따르세요.
"""
import argparse
import csv
import os
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP


def d(v):
    return Decimal((v or "0").replace(",", "").strip() or "0")


def main():
    ap = argparse.ArgumentParser(description="외화 채권·채무 기말 환산손익 계산")
    ap.add_argument("balances", help="외화 잔액 CSV (계정,거래처,구분(자산/부채),통화,외화금액,장부금액)")
    ap.add_argument("--rates", required=True, help="기말 환율 CSV (통화,환율,단위)")
    ap.add_argument("-o", "--out", default="out/fx_revaluation.csv")
    args = ap.parse_args()

    rates = {}
    with open(args.rates, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            unit = d(r.get("단위") or "1")
            rates[r["통화"].strip().upper()] = d(r["환율"]) / unit

    rows, problems = [], []
    by_acct = defaultdict(lambda: Decimal("0"))
    gain = loss = Decimal("0")
    with open(args.balances, encoding="utf-8-sig", newline="") as f:
        for i, r in enumerate(csv.DictReader(f), start=2):
            cur = r["통화"].strip().upper()
            side = r["구분"].strip()
            if cur not in rates:
                problems.append(f"{i}행: 통화 {cur} 의 기말 환율이 없음 → 건너뜀")
                continue
            if side not in ("자산", "부채"):
                problems.append(f"{i}행: 구분 '{side}' 은 자산/부채 가 아님 → 건너뜀")
                continue
            fc, book = d(r["외화금액"]), d(r["장부금액"])
            new = (fc * rates[cur]).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
            pl = (new - book) if side == "자산" else (book - new)
            book_rate = (book / fc).quantize(Decimal("0.01")) if fc else Decimal("0")
            rows.append({"계정": r["계정"], "거래처": r["거래처"], "구분": side, "통화": cur,
                         "외화금액": fc, "장부금액": book, "장부환율": book_rate,
                         "기말환율": format(rates[cur].quantize(Decimal("0.0001")).normalize(), "f"),   # 1.4E+3 같은 지수 표기 방지
                         "기말평가액": new, "환산손익": pl, "손익구분": "이익" if pl > 0 else ("손실" if pl < 0 else "-")})
            by_acct[(r["계정"], cur)] += pl
            if pl > 0:
                gain += pl
            else:
                loss += -pl

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["계정"])
        w.writeheader()
        w.writerows(rows)

    print(f"외화 잔액 {len(rows)}건 평가")
    print("\n[계정·통화별 환산손익]")
    for (acct, cur), v in sorted(by_acct.items()):
        print(f"  {acct} ({cur}): {v:+,}원")
    print(f"\n외화환산이익 {gain:,}원 / 외화환산손실 {loss:,}원 / 순액 {gain - loss:+,}원")
    for p in problems:
        print("  [확인] " + p)
    print(f"결과 → {args.out}  (분개 참고용입니다. 회계 기준은 회사 규정을 따르세요)")


if __name__ == "__main__":
    main()
