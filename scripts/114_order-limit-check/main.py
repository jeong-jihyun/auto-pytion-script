"""주문 내역이 사전에 정한 한도를 넘었는지 사후 점검하는 스크립트.

생각의 흐름:
  1) 주문 시스템에는 한도 체크가 있지만, 설정 실수나 예외 처리로 새는 경우가 있습니다.
     그래서 하루 주문 내역을 다시 읽어 '사후 점검'을 합니다.
  2) 한도는 JSON 파일에 둡니다(코드 수정 없이 바꿀 수 있게).
     - 1회주문한도: 주문 1건 금액(수량×가격)
     - 계좌일누적한도: 계좌별 하루 누적 주문금액
     - 종목일누적한도: 계좌·종목별 하루 누적 주문금액
     - 가격괴리율: 기준가 대비 주문가격 차이(%)  ← 주문 CSV에 '기준가' 열이 있을 때만
  3) 주문을 시간순으로 따라가며 누적을 더하고, '처음 한도를 넘긴 주문'과 그 이후 주문을 표시합니다.
  4) 위반 목록 CSV를 만들고 유형별 건수를 보여 줍니다.
"""
import argparse
import csv
import json
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path


def num(s):
    return Decimal(str(s).replace(",", "").strip() or "0")


def main():
    p = argparse.ArgumentParser(description="주문 한도 사후 점검")
    p.add_argument("orders", type=Path, help="주문 CSV(주문번호,시각,계좌,종목,매매구분,수량,가격[,기준가])")
    p.add_argument("limits", type=Path, help="한도 JSON")
    p.add_argument("-o", "--output", type=Path, default=Path("output/limit_violations.csv"))
    a = p.parse_args()

    lim = json.loads(a.limits.read_text(encoding="utf-8"))
    per_order = num(lim.get("1회주문한도", 0))
    per_acct = num(lim.get("계좌일누적한도", 0))
    per_sym = num(lim.get("종목일누적한도", 0))
    band = num(lim.get("가격괴리율", 0))

    with a.orders.open(newline="", encoding="utf-8-sig") as fp:
        orders = sorted(csv.DictReader(fp), key=lambda r: r["시각"])
    acct_sum, sym_sum = defaultdict(Decimal), defaultdict(Decimal)
    out, kinds = [], Counter()
    for r in orders:
        amt = num(r["수량"]) * num(r["가격"])
        acct, sym = r["계좌"].strip(), r["종목"].strip()
        acct_sum[acct] += amt
        sym_sum[(acct, sym)] += amt
        problems = []
        if per_order and amt > per_order:
            problems.append(("1회주문한도초과", amt, per_order))
        if per_acct and acct_sum[acct] > per_acct:
            problems.append(("계좌일누적한도초과", acct_sum[acct], per_acct))
        if per_sym and sym_sum[(acct, sym)] > per_sym:
            problems.append(("종목일누적한도초과", sym_sum[(acct, sym)], per_sym))
        if band and r.get("기준가"):
            ref = num(r["기준가"])
            if ref:
                gap = abs(num(r["가격"]) - ref) / ref * 100
                if gap > band:
                    problems.append(("가격괴리율초과", gap.quantize(Decimal("0.01")), band))
        for kind, val, limit in problems:
            kinds[kind] += 1
            out.append([r["주문번호"], r["시각"], acct, sym, r["매매구분"], amt, kind, val, limit])

    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["주문번호", "시각", "계좌", "종목", "매매구분", "주문금액", "위반유형", "실제값", "한도"])
        w.writerows(out)
    print(f"주문 {len(orders)}건 점검, 위반 {len(out)}건 → {a.output}")
    for k, c in kinds.most_common():
        print(f"  {k}: {c}건")


if __name__ == "__main__":
    main()
