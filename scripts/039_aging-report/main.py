"""미수금 연령 분석(채권 에이징) 스크립트.

청구 CSV(거래처, 청구일, 금액, 입금액)에서 아직 못 받은 돈(미수금)을
'청구일로부터 며칠 지났는지'에 따라 구간별로 나눠 거래처별 표로 보여 줍니다.
구간: 30일 이하 / 31~60일 / 61~90일 / 90일 초과  (기준일은 --base-date, 기본은 오늘)
"""
import argparse
import csv
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

BUCKETS = ["30일 이하", "31~60일", "61~90일", "90일 초과"]


def bucket_of(days):
    if days <= 30:
        return 0
    if days <= 60:
        return 1
    if days <= 90:
        return 2
    return 3


def to_int(text):
    return int(str(text).replace(",", "").strip() or 0)


def main():
    p = argparse.ArgumentParser(description="미수금 연령 분석")
    p.add_argument("input", type=Path, help="CSV (열: 거래처,청구일,금액,입금액)")
    p.add_argument("--base-date", help="기준일 YYYY-MM-DD (기본: 오늘)")
    p.add_argument("-o", "--output", type=Path, default=Path("output/aging.csv"))
    a = p.parse_args()
    base = datetime.strptime(a.base_date, "%Y-%m-%d").date() if a.base_date else date.today()

    table = defaultdict(lambda: [0, 0, 0, 0])
    skipped = 0
    with a.input.open(newline="", encoding="utf-8-sig") as fp:
        for n, row in enumerate(csv.DictReader(fp), start=2):
            try:
                billed = datetime.strptime(row["청구일"].strip(), "%Y-%m-%d").date()
                due = to_int(row["금액"]) - to_int(row["입금액"])
            except (ValueError, KeyError):
                print(f"[건너뜀] {n}번째 줄을 읽을 수 없습니다: {row}")
                skipped += 1
                continue
            if due <= 0:
                continue  # 다 받은 건은 미수금이 아닙니다.
            table[row["거래처"].strip()][bucket_of((base - billed).days)] += due

    a.output.parent.mkdir(parents=True, exist_ok=True)
    totals = [0, 0, 0, 0]
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["거래처"] + BUCKETS + ["합계"])
        for client in sorted(table):
            vals = table[client]
            w.writerow([client] + vals + [sum(vals)])
            totals = [t + v for t, v in zip(totals, vals)]
        w.writerow(["전체"] + totals + [sum(totals)])
    print(f"기준일 {base}, 미수 거래처 {len(table)}곳, 미수금 합계 {sum(totals):,}원 -> {a.output}")
    for name, v in zip(BUCKETS, totals):
        print(f"  {name}: {v:,}원")
    if skipped:
        print(f"  (읽지 못한 줄 {skipped}개)")


if __name__ == "__main__":
    main()
