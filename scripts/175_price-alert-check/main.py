"""보유 종목의 매입가와 오늘 가격을 비교해 손절선·익절선·목표가에 닿은 종목을 골라 주는 스크립트.

생각의 흐름:
  1) 종목이 많아지면 '몇 % 빠지면 판다, 몇 % 오르면 일부 판다'는 원칙을 매일 눈으로 지키기 어렵습니다.
  2) 보유 CSV(종목, 수량, 매입가, 손절%, 익절%, 목표가)와 가격 CSV(종목, 현재가)를 종목 코드로 맞춥니다.
     손절%·익절%가 비어 있으면 --stop / --take 기본값을 씁니다.
  3) 수익률 = (현재가 - 매입가) / 매입가. 손절선 이하면 '손절', 익절선 이상이면 '익절',
     목표가가 있고 그 이상이면 '목표가 도달', 손절선까지 --near %p 이내면 '손절 근접'으로 표시합니다.
  4) 가격이 없는 종목도 놓치지 않게 따로 알려 줍니다.
  5) 이 스크립트는 알림 목록만 만듭니다. 주문은 하지 않으며 투자 판단은 사람이 합니다.
"""
import argparse
import csv
import os


def num(v):
    v = (v or "").replace(",", "").strip()
    return float(v) if v else None


def main():
    ap = argparse.ArgumentParser(description="보유 종목 손절·익절 기준 도달 점검")
    ap.add_argument("holdings", help="보유 CSV (종목코드,종목명,수량,매입가,손절%,익절%,목표가)")
    ap.add_argument("prices", help="가격 CSV (종목코드,현재가)")
    ap.add_argument("--stop", type=float, default=-10.0, help="기본 손절 %% (기본 -10)")
    ap.add_argument("--take", type=float, default=20.0, help="기본 익절 %% (기본 20)")
    ap.add_argument("--near", type=float, default=2.0, help="손절선까지 몇 %%p 남으면 '근접'으로 볼지 (기본 2)")
    ap.add_argument("-o", "--out", default="out/price_alert.csv")
    args = ap.parse_args()

    prices = {}
    with open(args.prices, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            prices[r["종목코드"].strip()] = num(r["현재가"])

    results, no_price = [], []
    with open(args.holdings, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            code = r["종목코드"].strip()
            qty, cost = num(r["수량"]), num(r["매입가"])
            cur = prices.get(code)
            if cur is None:
                no_price.append(f"{code} {r['종목명']}")
                continue
            stop = num(r.get("손절%"))
            take = num(r.get("익절%"))
            stop = args.stop if stop is None else stop
            take = args.take if take is None else take
            target = num(r.get("목표가"))
            ret = (cur - cost) / cost * 100
            if ret <= stop:
                status = "손절"
            elif target is not None and cur >= target:
                status = "목표가 도달"
            elif ret >= take:
                status = "익절"
            elif ret - stop <= args.near:
                status = "손절 근접"
            else:
                status = "정상"
            results.append({"종목코드": code, "종목명": r["종목명"], "수량": int(qty), "매입가": cost,
                            "현재가": cur, "수익률%": round(ret, 2), "손절%": stop, "익절%": take,
                            "목표가": target if target is not None else "", "평가손익": round((cur - cost) * qty),
                            "상태": status})

    order = {"손절": 0, "손절 근접": 1, "목표가 도달": 2, "익절": 3, "정상": 4}
    results.sort(key=lambda x: (order[x["상태"]], x["수익률%"]))
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(results[0].keys()) if results else ["종목코드"])
        w.writeheader()
        w.writerows(results)

    alerts = [x for x in results if x["상태"] != "정상"]
    print(f"보유 {len(results) + len(no_price)}종목 중 알림 {len(alerts)}건")
    for x in alerts:
        print(f"  [{x['상태']}] {x['종목명']}({x['종목코드']}) 매입 {x['매입가']:,.0f} → 현재 {x['현재가']:,.0f} "
              f"({x['수익률%']:+.2f}%, 기준 {x['손절%']}% / {x['익절%']}%) 평가손익 {x['평가손익']:,}원")
    for n in no_price:
        print(f"  [가격 없음] {n} — 가격 파일을 확인하세요")
    print(f"결과 → {args.out}  (주문은 하지 않습니다. 판단은 직접 하세요)")


if __name__ == "__main__":
    main()
