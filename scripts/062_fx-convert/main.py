"""CSV의 외화 금액을 환율표로 원화(또는 다른 통화)로 바꾸는 스크립트.

환율표 CSV(통화,환율)에는 '1 단위 통화 = 몇 기준통화'를 적습니다. (예: USD,1350.5)
날짜별 환율이 필요하면 환율표에 '날짜' 열을 넣으면 거래일과 같은 날짜 환율을 씁니다.
"""
import argparse
import csv
import sys
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from pathlib import Path


def load_rates(path):
    """환율표를 읽어 {(날짜, 통화): 환율} 로 만듭니다. 날짜 열이 없으면 날짜는 ''."""
    rates = {}
    with path.open(newline="", encoding="utf-8-sig") as fp:
        for r in csv.DictReader(fp):
            rates[(r.get("날짜", "").strip(), r["통화"].strip().upper())] = Decimal(r["환율"].replace(",", ""))
    return rates


def main():
    p = argparse.ArgumentParser(description="외화 금액 환산")
    p.add_argument("input", type=Path)
    p.add_argument("--rates", type=Path, required=True, help="환율표 CSV")
    p.add_argument("--amount-col", default="금액")
    p.add_argument("--currency-col", default="통화")
    p.add_argument("--date-col", default="", help="날짜별 환율을 쓸 때 거래일 열 이름")
    p.add_argument("--base", default="KRW", help="기준 통화 이름(출력 열 이름용)")
    p.add_argument("-o", "--output", type=Path, default=Path("output/converted.csv"))
    a = p.parse_args()

    rates = load_rates(a.rates)
    rows_out, missing = [], 0
    with a.input.open(newline="", encoding="utf-8-sig") as fp:
        r = csv.DictReader(fp)
        fields = r.fieldnames or []
        for need in (a.amount_col, a.currency_col):
            if need not in fields:
                print(f"[오류] 없는 열: {need} (있는 열: {fields})")
                sys.exit(1)
        for ln, row in enumerate(r, start=2):
            cur = row[a.currency_col].strip().upper()
            date = row[a.date_col].strip() if a.date_col else ""
            rate = Decimal(1) if cur == a.base.upper() else rates.get((date, cur))
            try:
                amt = Decimal(row[a.amount_col].replace(",", ""))
            except InvalidOperation:
                amt = None
            if rate is None or amt is None:
                row[f"{a.base}환산"], row["적용환율"], row["비고"] = "", "", "환율 또는 금액 없음"
                missing += 1
            else:
                row[f"{a.base}환산"] = str((amt * rate).quantize(Decimal("1"), ROUND_HALF_UP))
                row["적용환율"], row["비고"] = str(rate), ""
            rows_out.append(row)

    a.output.parent.mkdir(parents=True, exist_ok=True)
    cols = fields + [f"{a.base}환산", "적용환율", "비고"]
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.DictWriter(fp, fieldnames=cols)
        w.writeheader()
        w.writerows(rows_out)
    print(f"{len(rows_out)}건 처리, 환율 없는 건 {missing}건 → {a.output}")


if __name__ == "__main__":
    main()
