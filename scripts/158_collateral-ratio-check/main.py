"""신용(대출) 계좌의 담보비율을 계산해 '추가 담보 요구'·'반대매매 대상' 후보를 미리 찾는 스크립트.

생각의 흐름:
  1) 담보비율(%) = 담보평가금액 ÷ 대출금(융자금+미수 이자 등) × 100
     담보평가금액 = Σ(보유수량 × 종가 × 담보인정비율) + 예수금
  2) 회사 규정에 따라 보통 두 선이 있습니다.
       - 유지비율(예: 140%) 아래 → 추가 담보 요구(마진콜) 대상
       - 반대매매 기준(예: 130%) 아래 → 반대매매 대상 후보
  3) 입력은 두 CSV입니다.
       - 보유(positions): 계좌,종목,수량  /  가격(prices): 종목,종가,담보인정비율%
       - 대출(loans): 계좌,대출금,예수금
  4) 부족 금액도 같이 냅니다: 유지비율로 되돌리려면 담보가 얼마나 더 필요한지
       부족액 = 대출금 × 유지비율 − 담보평가금액
  5) 가격이 없는 종목은 0원으로 보지 않고 '가격 없음' 경고로 따로 알립니다(잘못된 반대매매 방지).
  6) --shock -10 처럼 주면 '내일 10% 하락하면?' 스트레스 상황도 볼 수 있습니다.
  ※ 실제 반대매매·통지는 회사 시스템과 규정으로 하고, 이 스크립트는 사전 점검용입니다.
"""
import argparse
import csv
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP


def d(s):
    return Decimal(str(s).replace(",", "").strip() or "0")


def main():
    p = argparse.ArgumentParser(description="신용계좌 담보비율 점검")
    p.add_argument("positions")
    p.add_argument("prices")
    p.add_argument("loans")
    p.add_argument("--maintain", type=Decimal, default=Decimal(140), help="유지비율%% (기본 140)")
    p.add_argument("--liquidate", type=Decimal, default=Decimal(130), help="반대매매 기준%% (기본 130)")
    p.add_argument("--shock", type=Decimal, default=Decimal(0), help="가격 충격%% (예: -10)")
    p.add_argument("-o", "--output", default="collateral.out.csv")
    a = p.parse_args()

    prices = {r["종목"].strip(): (d(r["종가"]) * (1 + a.shock / 100), d(r["담보인정비율%"]) / 100)
              for r in csv.DictReader(open(a.prices, encoding="utf-8-sig"))}
    coll = defaultdict(Decimal)
    missing = defaultdict(list)
    for r in csv.DictReader(open(a.positions, encoding="utf-8-sig")):
        acct, code = r["계좌"].strip(), r["종목"].strip()
        if code not in prices:
            missing[acct].append(code)
            continue
        px, ratio = prices[code]
        coll[acct] += d(r["수량"]) * px * ratio

    out = []
    for r in csv.DictReader(open(a.loans, encoding="utf-8-sig")):
        acct = r["계좌"].strip()
        loan = d(r["대출금"])
        value = coll[acct] + d(r.get("예수금", 0))
        ratio = (value / loan * 100).quantize(Decimal("0.01"), ROUND_HALF_UP) if loan > 0 else None
        if missing[acct]:
            grade = "확인필요"
        elif ratio is None:
            grade = "대출없음"
        elif ratio < a.liquidate:
            grade = "반대매매후보"
        elif ratio < a.maintain:
            grade = "추가담보요구"
        else:
            grade = "정상"
        short = max(Decimal(0), loan * a.maintain / 100 - value).quantize(Decimal("1"), ROUND_HALF_UP)
        out.append({"계좌": acct, "담보평가금액": f"{value.quantize(Decimal('1'), ROUND_HALF_UP):f}",
                    "대출금": f"{loan:f}", "담보비율%": "" if ratio is None else f"{ratio:f}",
                    "판정": grade, "유지비율까지부족액": f"{short:f}",
                    "비고": f"가격 없음: {','.join(missing[acct])}" if missing[acct] else ""})
    order = {"반대매매후보": 0, "추가담보요구": 1, "확인필요": 2, "정상": 3, "대출없음": 4}
    out.sort(key=lambda r: (order[r["판정"]], Decimal(r["담보비율%"] or 99999)))

    with open(a.output, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()) if out else ["계좌"])
        w.writeheader()
        w.writerows(out)
    print(f"계좌 {len(out)}개 / 유지 {a.maintain}% · 반대매매 {a.liquidate}% · 가격충격 {a.shock}% → {a.output}")
    for r in out:
        print(f"  [{r['판정']}] {r['계좌']} 담보비율 {r['담보비율%'] or '-'}% "
              f"부족액 {Decimal(r['유지비율까지부족액']):,}원 {r['비고']}")


if __name__ == "__main__":
    main()
