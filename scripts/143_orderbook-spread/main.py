"""호가(오더북) 스냅샷 CSV로 스프레드·중간가·호가 불균형을 계산하는 스크립트.

생각의 흐름:
  1) 증권 시스템에서 호가 데이터는 '시각, 종목, 매수1~N호가/잔량, 매도1~N호가/잔량' 형태로 쌓입니다.
  2) 시장 상태를 볼 때 자주 쓰는 지표는 이렇습니다.
       - 스프레드      = 매도1호가 - 매수1호가 (원), bp = 스프레드 / 중간가 × 10000
       - 중간가        = (매도1 + 매수1) / 2
       - 가중 중간가   = (매수1 × 매도1잔량 + 매도1 × 매수1잔량) / (매수1잔량 + 매도1잔량)
       - 호가 불균형   = (매수잔량합 - 매도잔량합) / (매수잔량합 + 매도잔량합), +면 매수 우위
  3) 스냅샷마다 지표를 계산해 CSV로 저장하고, 종목별 평균·최대 스프레드와 평균 불균형을 요약합니다.
  4) 매도1 <= 매수1 인 '역전(crossed) 호가'나 호가가 비어 있는 줄은 데이터 이상으로 따로 셉니다.
  5) 열 이름 규칙: bid1, bid1_qty, ask1, ask1_qty, bid2 ... 처럼 숫자로 단계를 붙입니다. 단계 수는 자동으로 찾습니다.
"""
import argparse
import csv
import re
from collections import defaultdict


def num(x):
    try:
        return float(str(x).replace(",", ""))
    except (TypeError, ValueError):
        return None


def main():
    p = argparse.ArgumentParser(description="호가 스프레드·불균형 계산")
    p.add_argument("input", help="호가 스냅샷 CSV (time, symbol, bid1, bid1_qty, ask1, ask1_qty, ...)")
    p.add_argument("-o", "--output", default="orderbook_metrics.out.csv")
    p.add_argument("--levels", type=int, default=0, help="불균형 계산에 쓸 호가 단계 수 (0=있는 만큼 전부)")
    p.add_argument("--wide-bp", type=float, default=20.0, help="스프레드가 이 bp 이상이면 WIDE 표시 (기본 20)")
    p.add_argument("--encoding", default="utf-8-sig")
    a = p.parse_args()

    with open(a.input, encoding=a.encoding, newline="") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames or []
        found = sorted({int(m.group(1)) for c in cols for m in [re.fullmatch(r"bid(\d+)", c)] if m})
        if not found:
            raise SystemExit("[오류] bid1 같은 호가 열을 찾지 못했습니다.")
        levels = found if a.levels <= 0 else [n for n in found if n <= a.levels]
        rows = list(reader)

    out = []
    summary = defaultdict(lambda: {"n": 0, "sum_bp": 0.0, "max_bp": 0.0, "sum_imb": 0.0, "wide": 0})
    bad = defaultdict(int)
    for r in rows:
        sym = r.get("symbol", "")
        b1, a1 = num(r.get("bid1")), num(r.get("ask1"))
        bq1, aq1 = num(r.get("bid1_qty")), num(r.get("ask1_qty"))
        if not b1 or not a1 or bq1 is None or aq1 is None:
            bad["EMPTY"] += 1
            continue
        if a1 <= b1:
            bad["CROSSED"] += 1
            continue
        mid = (a1 + b1) / 2
        spread = a1 - b1
        bp = spread / mid * 10000
        micro = (b1 * aq1 + a1 * bq1) / (bq1 + aq1) if (bq1 + aq1) else mid
        bsum = sum(num(r.get(f"bid{n}_qty")) or 0 for n in levels)
        asum = sum(num(r.get(f"ask{n}_qty")) or 0 for n in levels)
        imb = (bsum - asum) / (bsum + asum) if (bsum + asum) else 0.0
        wide = bp >= a.wide_bp
        out.append([r.get("time", ""), sym, f"{b1:g}", f"{a1:g}", f"{spread:g}", f"{bp:.2f}",
                    f"{mid:.2f}", f"{micro:.2f}", f"{bsum:g}", f"{asum:g}", f"{imb:+.3f}", "WIDE" if wide else ""])
        s = summary[sym]
        s["n"] += 1
        s["sum_bp"] += bp
        s["max_bp"] = max(s["max_bp"], bp)
        s["sum_imb"] += imb
        s["wide"] += wide

    with open(a.output, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["time", "symbol", "bid1", "ask1", "spread", "spread_bp", "mid", "weighted_mid",
                    "bid_qty_sum", "ask_qty_sum", "imbalance", "flag"])
        w.writerows(out)

    print(f"스냅샷 {len(rows)}줄 중 {len(out)}줄 계산 (호가 단계 {len(levels)}개 사용) → {a.output}")
    print(f"{'종목':8s} {'건수':>4s} {'평균bp':>8s} {'최대bp':>8s} {'평균불균형':>10s} {'WIDE':>5s}")
    for sym, s in sorted(summary.items()):
        print(f"{sym:8s} {s['n']:4d} {s['sum_bp']/s['n']:8.2f} {s['max_bp']:8.2f} {s['sum_imb']/s['n']:+10.3f} {s['wide']:5d}")
    for k, v in bad.items():
        print(f"[데이터 이상] {k}: {v}줄 (EMPTY=호가 비어 있음, CROSSED=매도1<=매수1)")


if __name__ == "__main__":
    main()
