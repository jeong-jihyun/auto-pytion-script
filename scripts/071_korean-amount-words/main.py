"""숫자 금액을 한글 금액(예: 일금 일백이십삼만사천원정)으로 바꾸는 스크립트.

계약서·영수증·청구서에는 위조를 막으려고 금액을 한글로도 적습니다.
생각의 흐름:
  1) 숫자를 4자리씩 끊습니다(만·억·조 단위).
  2) 4자리 안에서는 천·백·십·일 자리를 읽습니다.
  3) 묶음마다 단위(만·억·조)를 붙여 이어 씁니다.
한 개 금액을 바로 바꾸거나, CSV의 금액 열을 통째로 바꿀 수 있습니다.
"""
import argparse
import csv
import sys
from pathlib import Path

DIGITS = ["", "일", "이", "삼", "사", "오", "육", "칠", "팔", "구"]
SMALL = ["", "십", "백", "천"]
BIG = ["", "만", "억", "조", "경"]


def four_digits(n, formal):
    """0~9999를 한글로 읽습니다. formal=True면 '일십', '일백'처럼 '일'을 생략하지 않습니다."""
    out = []
    for pos in range(3, -1, -1):
        d = (n // (10 ** pos)) % 10
        if d == 0:
            continue
        word = DIGITS[d]
        if d == 1 and pos > 0 and not formal:
            word = ""  # 일상 표기: '십', '백'
        out.append(word + SMALL[pos])
    return "".join(out)


def to_korean(amount, formal=True):
    """정수 금액을 한글로 바꿉니다. 0이면 '영'."""
    if amount == 0:
        return "영"
    if amount < 0:
        return "마이너스 " + to_korean(-amount, formal)
    parts, i = [], 0
    while amount > 0:
        chunk = amount % 10000
        if chunk:
            if i >= len(BIG):
                raise ValueError("너무 큰 금액입니다")
            parts.append(four_digits(chunk, formal) + BIG[i])
        amount //= 10000
        i += 1
    return "".join(reversed(parts))


def parse_amount(text):
    """'1,234,000' 처럼 쉼표가 있어도 정수로 읽습니다. 소수점이 있으면 오류로 봅니다."""
    s = (text or "").replace(",", "").replace("원", "").strip()
    if not s.lstrip("-").isdigit():
        raise ValueError(f"정수 금액이 아닙니다: {text!r}")
    return int(s)


def main():
    p = argparse.ArgumentParser(description="숫자 금액 → 한글 금액")
    p.add_argument("--amount", help="금액 하나만 바꿀 때(예: 1234000)")
    p.add_argument("--input", type=Path, help="CSV 파일(금액 열을 통째로 바꿀 때)")
    p.add_argument("--col", default="금액", help="금액 열 이름")
    p.add_argument("--plain", action="store_true", help="'일십/일백' 대신 '십/백'으로 씀")
    p.add_argument("--no-wrap", action="store_true", help="'일금 ~원정' 꾸밈 없이 숫자 부분만")
    p.add_argument("-o", "--output", type=Path, default=Path("output/amount_korean.csv"))
    a = p.parse_args()

    def fmt(n):
        k = to_korean(n, formal=not a.plain)
        return k if a.no_wrap else f"일금 {k}원정"

    if a.amount:
        print(fmt(parse_amount(a.amount)))
        return
    if not a.input:
        p.error("--amount 또는 --input 중 하나는 필요합니다")

    with a.input.open(newline="", encoding="utf-8-sig") as fp:
        r = csv.DictReader(fp)
        fields = list(r.fieldnames or [])
        if a.col not in fields:
            print(f"[오류] 없는 열: {a.col} (있는 열: {fields})")
            sys.exit(1)
        rows = list(r)
    new_col = a.col + "_한글"
    bad = 0
    for row in rows:
        try:
            row[new_col] = fmt(parse_amount(row[a.col]))
        except ValueError as e:
            row[new_col] = f"[확인필요] {e}"
            bad += 1
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.DictWriter(fp, fieldnames=fields + [new_col])
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)}건 변환(확인필요 {bad}건) → {a.output}")


if __name__ == "__main__":
    main()
