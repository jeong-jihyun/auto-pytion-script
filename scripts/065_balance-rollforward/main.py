"""계좌·원장의 잔액이 맞는지 검증하는 스크립트(이월 검증).

각 줄에서 '이전 잔액 + 입금 - 출금 = 현재 잔액'이 맞는지 계산해서 어긋난 줄을 찾습니다.
계좌별로 나누어 확인할 수 있고, 첫 줄의 잔액은 시작값으로 인정합니다.
금액은 Decimal로 계산해 소수점 오차가 없습니다.
"""
import argparse
import csv
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path


def num(s):
    s = (s or "").replace(",", "").strip()
    return Decimal(s) if s else Decimal(0)


def main():
    p = argparse.ArgumentParser(description="잔액 이월 검증")
    p.add_argument("input", type=Path)
    p.add_argument("--account-col", default="", help="계좌 구분 열(없으면 전체를 한 계좌로 봄)")
    p.add_argument("--in-col", default="입금")
    p.add_argument("--out-col", default="출금")
    p.add_argument("--balance-col", default="잔액")
    p.add_argument("-o", "--output", type=Path, default=Path("output/balance_errors.csv"))
    a = p.parse_args()

    with a.input.open(newline="", encoding="utf-8-sig") as fp:
        r = csv.DictReader(fp)
        fields = r.fieldnames or []
        for need in (a.in_col, a.out_col, a.balance_col) + ((a.account_col,) if a.account_col else ()):
            if need not in fields:
                print(f"[오류] 없는 열: {need} (있는 열: {fields})")
                sys.exit(1)
        rows = list(enumerate(r, start=2))

    prev, errors, checked = {}, [], 0
    for ln, row in rows:
        acct = row[a.account_col] if a.account_col else "(전체)"
        try:
            cur = num(row[a.balance_col])
            delta = num(row[a.in_col]) - num(row[a.out_col])
        except InvalidOperation:
            errors.append({"줄": ln, "계좌": acct, "문제": "금액을 숫자로 읽을 수 없음", "기대잔액": "", "실제잔액": "", "차이": ""})
            continue
        if acct in prev:
            checked += 1
            expect = prev[acct] + delta
            if expect != cur:
                errors.append({"줄": ln, "계좌": acct, "문제": "잔액 불일치", "기대잔액": str(expect), "실제잔액": str(cur), "차이": str(cur - expect)})
        prev[acct] = cur  # 틀렸더라도 실제 잔액을 기준으로 다음 줄을 이어서 검사

    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.DictWriter(fp, fieldnames=["줄", "계좌", "문제", "기대잔액", "실제잔액", "차이"])
        w.writeheader()
        w.writerows(errors)
    print(f"검사 {checked}건, 어긋난 곳 {len(errors)}건 → {a.output}")
    sys.exit(0)


if __name__ == "__main__":
    main()
