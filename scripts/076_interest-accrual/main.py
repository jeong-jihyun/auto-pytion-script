"""예금·채권·대여금의 기간 이자(경과이자)를 일수 계산 방식별로 계산하는 스크립트.

이자 = 원금 × 연이율 × (일수 / 1년 일수) 이지만, '일수'와 '1년 일수'를 세는 규칙이 여러 가지입니다.
  - ACT/365 : 실제 일수 / 365 (국내 예금·대출에 흔함)
  - ACT/360 : 실제 일수 / 360 (외화 단기자금에 흔함)
  - 30/360  : 한 달을 30일로 보고 센 일수 / 360 (채권 일부)
  - ACT/ACT : 해마다 실제 일수(365 또는 366)로 나눠 연도별로 더함
생각의 흐름: 시작일 포함, 종료일 제외(양편 넣기 아님)로 일수를 세고, 원 미만은 버립니다.
--as-of 를 주면 그날까지의 경과이자(미수이자)를 계산합니다.
"""
import argparse
import csv
import sys
from datetime import date
from decimal import Decimal, ROUND_FLOOR
from pathlib import Path


def days_30_360(d1, d2):
    """미국식(30/360 US) 간단 규칙: 31일은 30일로 봅니다."""
    y1, m1, dd1 = d1.year, d1.month, min(d1.day, 30)
    y2, m2, dd2 = d2.year, d2.month, d2.day
    if dd2 == 31 and dd1 == 30:
        dd2 = 30
    return (y2 - y1) * 360 + (m2 - m1) * 30 + (dd2 - dd1)


def year_fraction(d1, d2, basis):
    if basis == "ACT/365":
        return Decimal((d2 - d1).days), Decimal((d2 - d1).days) / 365
    if basis == "ACT/360":
        return Decimal((d2 - d1).days), Decimal((d2 - d1).days) / 360
    if basis == "30/360":
        n = days_30_360(d1, d2)
        return Decimal(n), Decimal(n) / 360
    if basis == "ACT/ACT":
        frac, cur = Decimal(0), d1
        while cur < d2:
            nxt = min(date(cur.year + 1, 1, 1), d2)
            ylen = 366 if (cur.year % 4 == 0 and (cur.year % 100 != 0 or cur.year % 400 == 0)) else 365
            frac += Decimal((nxt - cur).days) / ylen
            cur = nxt
        return Decimal((d2 - d1).days), frac
    raise ValueError(f"모르는 방식: {basis}")


def main():
    p = argparse.ArgumentParser(description="기간 이자(경과이자) 계산")
    p.add_argument("input", type=Path, help="CSV(계약번호,원금,연이율(%),시작일,만기일,방식)")
    p.add_argument("--as-of", help="이 날짜까지의 경과이자(YYYY-MM-DD). 없으면 만기까지")
    p.add_argument("-o", "--output", type=Path, default=Path("output/interest.csv"))
    a = p.parse_args()
    asof = date.fromisoformat(a.as_of) if a.as_of else None

    out, bad, total = [], 0, Decimal(0)
    with a.input.open(newline="", encoding="utf-8-sig") as fp:
        for r in csv.DictReader(fp):
            try:
                principal = Decimal(r["원금"].replace(",", ""))
                rate = Decimal(r["연이율"].replace("%", "")) / 100
                d1, d2 = date.fromisoformat(r["시작일"]), date.fromisoformat(r["만기일"])
                end = min(d2, asof) if asof else d2
                basis = r["방식"].strip().upper()
                if end <= d1:
                    n, frac = Decimal(0), Decimal(0)
                else:
                    n, frac = year_fraction(d1, end, basis)
            except (ValueError, KeyError, ArithmeticError) as e:
                print(f"[건너뜀] {r.get('계약번호')}: {e}")
                bad += 1
                continue
            interest = (principal * rate * frac).quantize(Decimal(1), rounding=ROUND_FLOOR)
            total += interest
            out.append({"계약번호": r["계약번호"], "방식": basis, "계산종료일": end.isoformat(),
                        "일수": str(n), "연분율": f"{frac:.6f}", "이자": str(interest)})
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.DictWriter(fp, fieldnames=["계약번호", "방식", "계산종료일", "일수", "연분율", "이자"])
        w.writeheader()
        w.writerows(out)
    print(f"{len(out)}건 계산, 이자 합계 {total:,}원(건너뜀 {bad}건) → {a.output}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
