"""배당금 입금 내역으로 종목별 연간 배당, 월별 배당 현금흐름, 배당수익률을 정리하는 스크립트.

생각의 흐름:
  1) 배당 내역(지급일, 종목, 세전배당금, 원천징수세액)을 읽어 세후 = 세전 - 세금 을 계산합니다.
  2) 연도·종목별 합계 → '어떤 종목이 배당을 많이 주나'
  3) 연도·월별 합계 → '몇 월에 돈이 들어오나'(배당 달력). 비는 달도 0으로 보여 줍니다.
  4) 보유 파일(종목, 보유수량, 매입단가)이 있으면 '투자원금 대비 배당수익률(세전)'을 계산합니다.
"""
import argparse
import csv
from collections import defaultdict
from pathlib import Path


def num(x):
    return float((x or "0").replace(",", "").strip() or 0)


def main():
    p = argparse.ArgumentParser(description="배당 내역 요약")
    p.add_argument("dividends", type=Path, help="CSV(지급일,종목,세전배당금,원천징수세액)")
    p.add_argument("--holdings", type=Path, help="CSV(종목,보유수량,매입단가) — 수익률 계산용")
    p.add_argument("--year", default="", help="특정 연도만(예: 2026)")
    p.add_argument("-o", "--outdir", type=Path, default=Path("output"))
    a = p.parse_args()

    by_stock = defaultdict(lambda: [0.0, 0.0, 0])
    by_month = defaultdict(lambda: [0.0, 0.0])
    years = set()
    with a.dividends.open(newline="", encoding="utf-8-sig") as fp:
        for r in csv.DictReader(fp):
            day = r["지급일"].strip().replace(".", "-")
            y, m = day[:4], day[5:7]
            if a.year and y != a.year:
                continue
            years.add(y)
            gross, tax = num(r["세전배당금"]), num(r.get("원천징수세액"))
            s = by_stock[(y, r["종목"].strip())]
            s[0] += gross
            s[1] += gross - tax
            s[2] += 1
            mm = by_month[(y, m)]
            mm[0] += gross
            mm[1] += gross - tax

    cost = {}
    if a.holdings:
        with a.holdings.open(newline="", encoding="utf-8-sig") as fp:
            for r in csv.DictReader(fp):
                cost[r["종목"].strip()] = num(r["보유수량"]) * num(r["매입단가"])

    a.outdir.mkdir(parents=True, exist_ok=True)
    with (a.outdir / "by_stock.csv").open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["연도", "종목", "지급횟수", "세전합계", "세후합계", "투자원금", "배당수익률%(세전)"])
        for (y, st), (g, n, c) in sorted(by_stock.items(), key=lambda x: (x[0][0], -x[1][0])):
            base = cost.get(st)
            w.writerow([y, st, c, int(g), int(n), int(base) if base else "",
                        round(g / base * 100, 2) if base else ""])
    with (a.outdir / "by_month.csv").open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["연도", "월", "세전", "세후"])
        for y in sorted(years):
            for m in range(1, 13):
                g, n = by_month.get((y, f"{m:02d}"), (0, 0))
                w.writerow([y, m, int(g), int(n)])

    for y in sorted(years):
        g = sum(v[0] for k, v in by_stock.items() if k[0] == y)
        n = sum(v[1] for k, v in by_stock.items() if k[0] == y)
        months = [m for m in range(1, 13) if (y, f"{m:02d}") in by_month]
        print(f"{y}년 배당 세전 {g:,.0f}원 / 세후 {n:,.0f}원, 입금 있는 달: {', '.join(map(str, months))}월")
        for (yy, st), (gg, nn, c) in sorted(by_stock.items(), key=lambda x: -x[1][0]):
            if yy == y:
                base = cost.get(st)
                rate = f", 수익률 {gg / base * 100:.2f}%" if base else ""
                print(f"  - {st}: {c}회 세전 {gg:,.0f}원{rate}")
    print(f"결과: {a.outdir / 'by_stock.csv'}, {a.outdir / 'by_month.csv'}")


if __name__ == "__main__":
    main()
