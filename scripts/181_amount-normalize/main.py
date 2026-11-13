"""CSV 안에 제각각으로 적힌 금액 글자를 계산할 수 있는 숫자로 통일하는 스크립트.

생각의 흐름:
  1) 여러 부서·시스템에서 받은 표를 보면 금액이 '1,234원', '₩ 12,000', '(5,000)', '△3,000',
     '1,000-', '3.5만', '1억 2,000만' 처럼 섞여 있어서 엑셀 합계가 맞지 않습니다.
  2) 먼저 통화 기호·'원'·쉼표·공백을 지웁니다.
  3) 음수 표시는 여러 가지입니다: 앞의 '-', 괄호 '( )', 회계에서 쓰는 '△'·'▲', 뒤에 붙은 '-'.
     하나라도 있으면 음수로 봅니다.
  4) '억'·'만'·'천' 단위가 있으면 덩어리별로 곱해서 더합니다. (예: 1억 2,000만 = 100,000,000 + 20,000,000)
  5) 숫자로 바꿀 수 없는 칸은 원래 글자를 그대로 두고 '문제 목록'에 줄 번호와 함께 적습니다.
     → 틀린 값을 조용히 0으로 바꾸면 합계가 틀어져도 모르기 때문입니다.
  6) 원본은 건드리지 않고 새 CSV로 저장합니다.
"""
import argparse
import csv
import re
import sys
from decimal import Decimal, InvalidOperation

UNITS = {"억": Decimal(100000000), "만": Decimal(10000), "천": Decimal(1000)}
STRIP_RE = re.compile(r"[₩￦$€¥,\s원]|KRW|USD|JPY|EUR", re.IGNORECASE)


def parse_amount(text):
    """금액 글자 하나를 Decimal 로 바꿉니다. 실패하면 ValueError."""
    s = (text or "").strip()
    if s == "":
        return None
    neg = False
    if s.startswith("(") and s.endswith(")"):
        neg, s = True, s[1:-1]
    s = STRIP_RE.sub("", s)
    if s[:1] in "△▲":
        neg, s = True, s[1:]
    if s.startswith("-"):
        neg, s = (not neg) if neg else True, s[1:]
    elif s.startswith("+"):
        s = s[1:]
    if s.endswith("-"):
        neg, s = True, s[:-1]
    if s == "":
        raise ValueError("숫자가 없습니다")

    # 억/만/천 단위 처리: '1억2000만5' → 1*억 + 2000*만 + 5
    if any(u in s for u in UNITS):
        total, rest = Decimal(0), s
        for unit, mul in UNITS.items():
            if unit in rest:
                head, rest = rest.split(unit, 1)
                if head == "":
                    head = "1"            # '만원' 처럼 앞 숫자가 없으면 1로 봅니다
                total += Decimal(head) * mul
        if rest:
            total += Decimal(rest)
        value = total
    else:
        try:
            value = Decimal(s)
        except InvalidOperation:
            raise ValueError("숫자로 바꿀 수 없습니다")
    return -value if neg else value


def fmt(value, decimals):
    if value is None:
        return ""
    q = Decimal(1).scaleb(-decimals) if decimals > 0 else Decimal(1)
    return str(value.quantize(q))


def main():
    ap = argparse.ArgumentParser(description="CSV 금액 글자를 숫자로 통일")
    ap.add_argument("input", help="입력 CSV (UTF-8 또는 UTF-8 BOM)")
    ap.add_argument("--columns", required=True, help="바꿀 열 이름, 쉼표로 구분 (예: 금액,수수료)")
    ap.add_argument("--output", default="output/normalized.csv", help="결과 CSV")
    ap.add_argument("--problems", default="output/problems.csv", help="숫자로 못 바꾼 칸 목록")
    ap.add_argument("--decimals", type=int, default=0, help="소수점 자리수 (기본 0, 반올림 방식은 은행가 반올림)")
    args = ap.parse_args()

    import os
    cols = [c.strip() for c in args.columns.split(",") if c.strip()]
    with open(args.input, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        missing = [c for c in cols if c not in fields]
        if missing:
            sys.exit(f"[오류] 입력 파일에 없는 열: {', '.join(missing)} (있는 열: {', '.join(fields)})")
        rows = list(reader)

    problems, changed = [], 0
    for i, row in enumerate(rows, start=2):           # 1행은 제목줄이라 데이터는 2행부터
        for c in cols:
            raw = row[c]
            try:
                new = fmt(parse_amount(raw), args.decimals)
            except (ValueError, InvalidOperation) as e:
                problems.append({"행": i, "열": c, "원래값": raw, "이유": str(e)})
                continue
            if new != raw:
                changed += 1
            row[c] = new

    for path in (args.output, args.problems):
        d = os.path.dirname(path)
        if d:
            os.makedirs(d, exist_ok=True)
    with open(args.output, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    with open(args.problems, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["행", "열", "원래값", "이유"])
        w.writeheader()
        w.writerows(problems)

    print(f"읽은 행: {len(rows)}, 바뀐 칸: {changed}, 못 바꾼 칸: {len(problems)}")
    for p in problems:
        print(f"  - {p['행']}행 [{p['열']}] '{p['원래값']}' → {p['이유']}")
    print(f"결과: {args.output}")
    print(f"문제 목록: {args.problems}")


if __name__ == "__main__":
    main()
