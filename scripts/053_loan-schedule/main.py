"""대출 상환 일정표(원리금균등 / 원금균등 / 만기일시)를 만드는 스크립트.

금액은 원 단위로 반올림하고, 마지막 회차에서 남은 원금을 정확히 맞춥니다.
이 표는 연습·검토용 '추정치'입니다. 실제 금융기관 계산(일할 이자, 말일 처리 등)과 다를 수 있습니다.
"""
import argparse
import csv
import sys
from pathlib import Path


def schedule(principal, annual_rate, months, method):
    """회차별 (회차, 상환원금, 이자, 납입액, 남은원금) 목록을 돌려줍니다."""
    r = annual_rate / 100 / 12                # 월 이율
    balance = principal
    rows = []
    if method == "equal-payment" and r > 0:
        pay = principal * r / (1 - (1 + r) ** -months)
    else:
        pay = principal / months if method == "equal-payment" else 0
    for n in range(1, months + 1):
        interest = round(balance * r)
        if method == "equal-payment":
            repay = round(pay) - interest
        elif method == "equal-principal":
            repay = round(principal / months)
        else:                                  # 만기일시: 마지막에만 원금
            repay = 0
        if n == months:                        # 마지막 회차에 남은 원금을 정확히 맞춤
            repay = balance
        balance -= repay
        rows.append((n, repay, interest, repay + interest, balance))
    return rows


def main():
    p = argparse.ArgumentParser(description="대출 상환 일정표 만들기")
    p.add_argument("--principal", type=int, required=True, help="대출 원금(원)")
    p.add_argument("--rate", type=float, required=True, help="연 이자율(%%)")
    p.add_argument("--months", type=int, required=True, help="상환 개월 수")
    p.add_argument("--method", choices=["equal-payment", "equal-principal", "bullet"],
                   default="equal-payment", help="원리금균등 / 원금균등 / 만기일시")
    p.add_argument("-o", "--output", type=Path, default=Path("output/loan.csv"))
    a = p.parse_args()
    if a.principal <= 0 or a.months <= 0 or a.rate < 0:
        print("[오류] 원금·개월은 1 이상, 이자율은 0 이상이어야 합니다.")
        sys.exit(1)

    rows = schedule(a.principal, a.rate, a.months, a.method)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["회차", "상환원금", "이자", "납입액", "남은원금"])
        w.writerows(rows)
    total_int = sum(x[2] for x in rows)
    print(f"[요약] {a.method} / 원금 {a.principal:,}원 / 연 {a.rate}% / {a.months}개월")
    print(f"  첫 회차 납입액 {rows[0][3]:,}원, 마지막 회차 {rows[-1][3]:,}원")
    print(f"  총 이자 {total_int:,}원, 총 납입 {a.principal + total_int:,}원 -> {a.output}")


if __name__ == "__main__":
    main()
