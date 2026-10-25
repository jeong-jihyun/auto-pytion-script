"""액면분할·병합을 반영해 과거 주가를 수정주가로 바꾸는 스크립트.

생각의 흐름:
  1) 분할(예: 1주를 5주로)이 있으면 그날 전의 가격은 '1/5'로 줄여야 앞뒤를 비교할 수 있습니다.
  2) 이벤트 CSV(일자,비율)에서 비율>1 은 분할, 0<비율<1 은 병합입니다.
  3) 각 가격 날짜보다 '뒤에 있는' 이벤트들의 비율을 모두 곱해 나눕니다.
  4) 원래 종가와 수정 종가를 같이 보여 줍니다. 원본 파일은 건드리지 않습니다.
"""
import argparse
import csv
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description="수정주가 계산")
    p.add_argument("--prices", required=True, help="CSV(일자,종가)")
    p.add_argument("--events", required=True, help="CSV(일자,비율) 분할일 기준")
    p.add_argument("--out", default="output/수정주가.csv")
    a = p.parse_args()

    with open(a.events, encoding="utf-8-sig", newline="") as f:
        events = [(r["일자"], Decimal(r["비율"])) for r in csv.DictReader(f)]
    with open(a.prices, encoding="utf-8-sig", newline="") as f:
        prices = list(csv.DictReader(f))

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["일자", "종가", "수정종가", "적용비율"])
        for r in prices:
            factor = Decimal(1)
            for d, ratio in events:
                if r["일자"] < d:  # 분할일 '전'의 가격만 조정합니다
                    factor *= ratio
            close = Decimal(r["종가"].replace(",", ""))
            adj = (close / factor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            w.writerow([r["일자"], close, adj, factor])
            print(f"{r['일자']} 종가 {close:,} -> 수정 {adj:,} (비율 {factor})")


if __name__ == "__main__":
    main()
