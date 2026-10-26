"""품목별 구매 단가가 어떻게 변해 왔는지 정리하고, 직전보다 크게 오른 구매를 표시하는 스크립트.

생각의 흐름:
  1) 같은 품목인데 어느 날 단가가 확 오르면 단가 계약 위반·입력 실수·단가 인상 미보고일 수 있습니다.
  2) 구매 내역(일자, 품목, 거래처, 수량, 단가)을 품목별로 묶고 날짜순으로 줄 세웁니다.
  3) 각 구매마다 '직전 구매 대비 변동률'을 계산하고, 기준(%)을 넘게 오르거나 내리면 표시합니다.
  4) 품목별 요약(최저·최고·최근 단가, 수량가중 평균 단가, 처음 대비 변동률)도 만듭니다.
     수량가중 평균 = 총금액 ÷ 총수량 (많이 산 단가에 더 무게를 줌)
"""
import argparse
import csv
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


def num(s):
    return Decimal(str(s).replace(",", "").strip())


def r2(x):
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def main():
    p = argparse.ArgumentParser(description="품목별 구매 단가 이력·급등 경고")
    p.add_argument("purchases", type=Path, help="CSV(일자,품목,거래처,수량,단가)")
    p.add_argument("--threshold", type=Decimal, default=Decimal("10"), help="직전 대비 이 % 이상 변하면 표시(기본 10)")
    p.add_argument("-o", "--outdir", type=Path, default=Path("output"))
    a = p.parse_args()

    by_item = defaultdict(list)
    with a.purchases.open(newline="", encoding="utf-8-sig") as fp:
        for r in csv.DictReader(fp):
            by_item[r["품목"].strip()].append(
                (r["일자"].strip(), r["거래처"].strip(), num(r["수량"]), num(r["단가"])))

    history, summary, alerts = [], [], 0
    for item, rows in sorted(by_item.items()):
        rows.sort(key=lambda x: x[0])
        prev = None
        for day, vendor, qty, price in rows:
            change, flag = "", ""
            if prev:
                ch = (price - prev) / prev * 100
                change = r2(ch)
                if ch >= a.threshold:
                    flag, alerts = "급등", alerts + 1
                elif ch <= -a.threshold:
                    flag, alerts = "급락", alerts + 1
            history.append([item, day, vendor, qty, price, prev or "", change, flag])
            prev = price
        prices = [x[3] for x in rows]
        tq = sum(x[2] for x in rows)
        wavg = r2(sum(x[2] * x[3] for x in rows) / tq) if tq else ""
        first, last = prices[0], prices[-1]
        summary.append([item, len(rows), min(prices), max(prices), last, wavg, r2((last - first) / first * 100)])

    a.outdir.mkdir(parents=True, exist_ok=True)
    with (a.outdir / "price_history.csv").open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["품목", "일자", "거래처", "수량", "단가", "직전단가", "직전대비%", "표시"])
        w.writerows(history)
    with (a.outdir / "price_summary.csv").open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["품목", "구매횟수", "최저단가", "최고단가", "최근단가", "수량가중평균단가", "처음대비%"])
        w.writerows(summary)

    print(f"품목 {len(summary)}개, 구매 {len(history)}건, 직전 대비 ±{a.threshold}% 이상 변동 {alerts}건 → {a.outdir}")
    for h in history:
        if h[7]:
            print(f"  [{h[7]}] {h[0]} {h[1]} {h[2]}: {h[5]:,} → {h[4]:,} ({h[6]}%)")


if __name__ == "__main__":
    main()
