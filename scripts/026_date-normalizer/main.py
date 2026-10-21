"""날짜 형식 통일 스크립트.

CSV 의 날짜 열에 2026.10.21 / 2026/10/21 / 20261021 / 2026년 10월 21일 / 10/21/2026 처럼
섞여 있는 형식을 모두 YYYY-MM-DD 로 바꿉니다.
'03/04/2026' 처럼 월/일이 헷갈리는 경우는 기본이 '월/일/년(미국식)'이고,
--dayfirst 를 주면 '일/월/년'으로 읽습니다. 읽지 못한 칸은 원래 값을 그대로 두고 목록으로 알려 줍니다.
"""
import argparse
import csv
import re
from datetime import date
from pathlib import Path


def parse(text, dayfirst):
    """글자 하나를 date 로 바꿉니다. 못 바꾸면 None."""
    t = text.strip()
    if not t:
        return None
    # 연도가 앞에 오는 형식: 2026-10-21, 2026.10.21, 2026/10/21, 2026년 10월 21일
    m = re.fullmatch(r"(\d{4})\s*[-./년]\s*(\d{1,2})\s*[-./월]\s*(\d{1,2})\s*일?", t)
    if not m:
        m = re.fullmatch(r"(\d{4})(\d{2})(\d{2})", t)  # 20261021
    if m:
        y, mo, d = (int(x) for x in m.groups())
    else:
        # 연도가 뒤에 오는 형식: 10/21/2026, 21-10-2026
        m = re.fullmatch(r"(\d{1,2})[-./](\d{1,2})[-./](\d{4})", t)
        if not m:
            return None
        first, second, y = (int(x) for x in m.groups())
        mo, d = (second, first) if dayfirst else (first, second)
    try:
        return date(y, mo, d)
    except ValueError:  # 2026-02-30 같은 없는 날짜
        return None


def main():
    p = argparse.ArgumentParser(description="날짜 형식을 YYYY-MM-DD 로 통일")
    p.add_argument("input", type=Path)
    p.add_argument("--columns", required=True, help="날짜 열 이름 (쉼표로 여러 개)")
    p.add_argument("--dayfirst", action="store_true", help="01/02/2026 을 일/월/년으로 읽음")
    p.add_argument("-o", "--output", type=Path, default=Path("output/dates_fixed.csv"))
    a = p.parse_args()
    cols = [c.strip() for c in a.columns.split(",")]

    with a.input.open(newline="", encoding="utf-8-sig") as fp:
        r = csv.DictReader(fp)
        header = r.fieldnames
        for c in cols:
            if c not in header:
                raise SystemExit(f"오류: '{c}' 열이 없습니다. 열 목록: {header}")
        rows = list(r)
    bad = []
    for i, row in enumerate(rows, start=2):  # 2 = 엑셀에서 보이는 줄 번호(머리글이 1)
        for c in cols:
            if not row[c].strip():
                continue
            d = parse(row[c], a.dayfirst)
            if d:
                row[c] = d.isoformat()
            else:
                bad.append((i, c, row[c]))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.DictWriter(fp, fieldnames=header)
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)}행 처리, 읽지 못한 칸 {len(bad)}개 -> {a.output}")
    for line, c, v in bad:
        print(f"  {line}줄 '{c}' 열: '{v}' (그대로 둠)")


if __name__ == "__main__":
    main()
