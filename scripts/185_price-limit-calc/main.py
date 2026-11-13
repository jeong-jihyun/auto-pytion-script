"""종목별 기준가격으로 다음 거래일의 상한가·하한가를 호가단위에 맞춰 계산하는 스크립트.

생각의 흐름:
  1) 주문 시스템 점검·테스트 데이터 준비 때 "이 종목 내일 상한가가 얼마지?"를 자주 계산합니다.
  2) 국내 주식은 기준가격의 ±30% 가 가격제한폭이고, 가격은 호가단위(1원, 5원, 10원 ...)에 맞아야 합니다.
  3) 계산 순서(이 스크립트가 쓰는 방식):
     a. 제한폭 = 기준가격 × 30% 를 '기준가격 구간의 호가단위' 미만은 버림
     b. 상한가 = 기준가격 + 제한폭 → 상한가 구간의 호가단위에 맞게 내림
     c. 하한가 = 기준가격 - 제한폭 → 하한가 구간의 호가단위에 맞게 올림
     (내림/올림 방향은 '제한폭 밖으로 나가지 않게' 하려는 것입니다)
  4) 호가단위표는 2023년 1월 개편된 유가증권·코스닥 공통 표를 기본으로 넣었고,
     제도가 바뀌면 --tick-file 로 새 표(CSV)를 줄 수 있게 했습니다.
  5) 돈 계산이라 부동소수점 대신 정수·Decimal 로 계산합니다.
"""
import argparse
import csv
import os
import sys
from decimal import Decimal, ROUND_FLOOR

# (이 가격 미만이면, 호가단위) - 마지막 줄은 그 이상 전부
DEFAULT_TICKS = [(2000, 1), (5000, 5), (20000, 10), (50000, 50),
                 (200000, 100), (500000, 500), (None, 1000)]


def load_ticks(path):
    if not path:
        return DEFAULT_TICKS
    table = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            upper = r["미만"].strip()
            table.append((int(upper) if upper else None, int(r["호가단위"])))
    return table


def tick_of(price, ticks):
    for upper, tick in ticks:
        if upper is None or price < upper:
            return tick
    return ticks[-1][1]


def floor_to(price, tick):
    return price // tick * tick


def ceil_to(price, tick):
    return -(-price // tick) * tick


def limits(base, rate, ticks):
    t0 = tick_of(base, ticks)
    width = int((Decimal(base) * rate).to_integral_value(rounding=ROUND_FLOOR))
    width = floor_to(width, t0)
    up = base + width
    up = floor_to(up, tick_of(up, ticks))
    low = max(base - width, 1)
    low = ceil_to(low, tick_of(low, ticks))
    return width, up, low


def main():
    ap = argparse.ArgumentParser(description="상한가·하한가 계산 (호가단위 반영)")
    ap.add_argument("input", help="종목 CSV (종목코드, 종목명, 기준가격 열)")
    ap.add_argument("--price-col", default="기준가격")
    ap.add_argument("--rate", default="0.30", help="가격제한폭 비율 (기본 0.30 = 30%%)")
    ap.add_argument("--tick-file", help="호가단위표 CSV (열: 미만,호가단위 / 마지막 줄 미만은 빈칸)")
    ap.add_argument("--output", default="output/price_limits.csv")
    args = ap.parse_args()

    rate = Decimal(args.rate)
    ticks = load_ticks(args.tick_file)
    with open(args.input, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fields = list(reader.fieldnames or [])
        if args.price_col not in fields:
            sys.exit(f"[오류] '{args.price_col}' 열이 없습니다. 있는 열: {fields}")
        rows = list(reader)

    out_fields = fields + ["호가단위", "제한폭", "상한가", "하한가", "비고"]
    for i, r in enumerate(rows, start=2):
        raw = r[args.price_col].replace(",", "").strip()
        r.update({"호가단위": "", "제한폭": "", "상한가": "", "하한가": "", "비고": ""})
        if not raw.isdigit() or int(raw) <= 0:
            r["비고"] = f"기준가격 '{r[args.price_col]}' 이(가) 양의 정수가 아님"
            continue
        base = int(raw)
        width, up, low = limits(base, rate, ticks)
        r.update({"호가단위": tick_of(base, ticks), "제한폭": width, "상한가": up, "하한가": low})
        if base % tick_of(base, ticks):
            r["비고"] = "기준가격이 호가단위에 안 맞음(입력 확인)"

    d = os.path.dirname(args.output)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(args.output, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=out_fields)
        w.writeheader()
        w.writerows(rows)

    name_col = "종목명" if "종목명" in fields else fields[0]
    print(f"{'종목':<10}{'기준가격':>12}{'상한가':>12}{'하한가':>12}  비고")
    for r in rows:
        bp = r[args.price_col]
        print(f"{r[name_col]:<10}{bp:>12}{str(r['상한가']):>12}{str(r['하한가']):>12}  {r['비고']}")
    print(f"저장: {args.output}")


if __name__ == "__main__":
    main()
