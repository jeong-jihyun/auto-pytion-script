"""분개(전표) 파일의 차변·대변이 맞는지 검사하고 계정별 시산표를 만드는 스크립트.

생각의 흐름:
  1) 분개 CSV(전표번호,일자,계정,차변,대변)를 읽습니다.
  2) 전표별로 차변 합과 대변 합을 비교해 다르면 '불균형 전표'로 표시합니다.
  3) 계정별로 차변·대변을 더해 시산표를 만들고 전체 합계도 비교합니다.
  4) 한 줄에 차변·대변이 둘 다 있거나 음수인 줄도 이상 징후로 알려 줍니다.
  불균형이 있으면 종료 코드 1 을 돌려줘서 배치 점검에도 쓸 수 있습니다.
"""
import argparse
import csv
import sys
from collections import defaultdict
from decimal import Decimal
from pathlib import Path


def money(t):
    t = (t or "").replace(",", "").strip()
    return Decimal(t) if t else Decimal(0)


def main():
    p = argparse.ArgumentParser(description="전표 차대 균형 검사")
    p.add_argument("--input", required=True, help="분개 CSV")
    p.add_argument("--out-dir", default="output")
    a = p.parse_args()

    slips = defaultdict(lambda: [Decimal(0), Decimal(0)])
    accts = defaultdict(lambda: [Decimal(0), Decimal(0)])
    odd = []
    with open(a.input, encoding="utf-8-sig", newline="") as f:
        for n, r in enumerate(csv.DictReader(f), start=2):
            d, c = money(r["차변"]), money(r["대변"])
            if d < 0 or c < 0 or (d and c):
                odd.append(f"{n}행(전표 {r['전표번호']}): 차변/대변 값이 이상합니다")
            slips[r["전표번호"]][0] += d
            slips[r["전표번호"]][1] += c
            accts[r["계정"]][0] += d
            accts[r["계정"]][1] += c

    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    bad = {k: v for k, v in slips.items() if v[0] != v[1]}
    with open(out / "불균형전표.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["전표번호", "차변합", "대변합", "차이"])
        for k, (d, c) in sorted(bad.items()):
            w.writerow([k, d, c, d - c])
    td = tc = Decimal(0)
    with open(out / "시산표.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["계정", "차변합", "대변합", "잔액(차변-대변)"])
        for k, (d, c) in sorted(accts.items()):
            w.writerow([k, d, c, d - c])
            td += d
            tc += c
        w.writerow(["합계", td, tc, td - tc])
    print(f"전표 {len(slips)}건 중 불균형 {len(bad)}건, 이상한 줄 {len(odd)}건")
    for k, (d, c) in sorted(bad.items()):
        print(f"  불균형 전표 {k}: 차변 {d:,} / 대변 {c:,}")
    for m in odd:
        print("  " + m)
    print(f"전체 차변 {td:,} / 대변 {tc:,} -> {'일치' if td == tc else '불일치'}")
    sys.exit(1 if bad or odd or td != tc else 0)


if __name__ == "__main__":
    main()
