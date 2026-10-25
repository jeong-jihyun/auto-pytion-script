"""은행 거래내역을 키워드 규칙으로 분류하고 분류별 합계를 내는 스크립트.

생각의 흐름:
  1) 규칙 CSV(키워드,분류)를 위에서부터 읽습니다. 먼저 맞는 규칙이 이깁니다.
  2) 거래내역 CSV(일자,적요,출금,입금)의 '적요'에 키워드가 들어 있으면 그 분류를 붙입니다.
  3) 어느 규칙에도 안 맞으면 '미분류'로 두어 사람이 규칙을 보강할 수 있게 합니다.
  4) 분류별 출금·입금 합계를 화면과 요약 CSV로 보여 줍니다.
"""
import argparse
import csv
from collections import defaultdict
from decimal import Decimal
from pathlib import Path


def money(text):
    text = (text or "").replace(",", "").strip()
    return Decimal(text) if text else Decimal(0)


def load_rules(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return [(r["키워드"].strip(), r["분류"].strip()) for r in csv.DictReader(f) if r["키워드"].strip()]


def classify(memo, rules):
    for keyword, name in rules:
        if keyword in memo:
            return name
    return "미분류"


def main():
    p = argparse.ArgumentParser(description="거래내역 자동 분류")
    p.add_argument("--input", required=True, help="거래내역 CSV(일자,적요,출금,입금)")
    p.add_argument("--rules", required=True, help="규칙 CSV(키워드,분류)")
    p.add_argument("--out-dir", default="output", help="결과 폴더")
    a = p.parse_args()

    rules = load_rules(a.rules)
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    sums = defaultdict(lambda: [Decimal(0), Decimal(0), 0])
    rows = []
    with open(a.input, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            cat = classify(r["적요"], rules)
            wd, dp = money(r["출금"]), money(r["입금"])
            s = sums[cat]
            s[0] += wd
            s[1] += dp
            s[2] += 1
            rows.append({**r, "분류": cat})
    with open(out / "분류결과.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    with open(out / "분류별합계.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["분류", "건수", "출금합계", "입금합계"])
        for cat, (wd, dp, n) in sorted(sums.items()):
            w.writerow([cat, n, wd, dp])
            print(f"{cat}: {n}건, 출금 {wd:,}, 입금 {dp:,}")
    print(f"완료: 총 {len(rows)}건 -> {out}")


if __name__ == "__main__":
    main()
