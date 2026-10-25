"""체결·주문 시각이 장 운영시간 안에 있는지 점검하는 스크립트(증권 시스템 점검용).

기본 정규장 09:00~15:30, 평일만 허용합니다(시간·휴일은 옵션으로 바꿈).
장 시작 전·마감 후·주말·휴일 시각의 건을 찾아 CSV로 모읍니다.
시간대 변환 없이 파일에 적힌 시각을 그대로 봅니다.
"""
import argparse
import csv
import sys
from datetime import datetime, time
from pathlib import Path


def hm(s):
    h, m = s.split(":")
    return time(int(h), int(m))


def main():
    p = argparse.ArgumentParser(description="장 운영시간 밖 거래 찾기")
    p.add_argument("input", type=Path)
    p.add_argument("--time-col", default="체결시각", help="'YYYY-MM-DD HH:MM:SS' 형식의 열")
    p.add_argument("--open", default="09:00")
    p.add_argument("--close", default="15:30")
    p.add_argument("--holidays", type=Path, help="휴장일 목록(한 줄에 YYYY-MM-DD)")
    p.add_argument("-o", "--output", type=Path, default=Path("output/off_hours.csv"))
    a = p.parse_args()

    op, cl = hm(a.open), hm(a.close)
    hol = set()
    if a.holidays:
        hol = {x.strip() for x in a.holidays.read_text(encoding="utf-8-sig").splitlines() if x.strip() and not x.startswith("#")}

    flagged, total = [], 0
    with a.input.open(newline="", encoding="utf-8-sig") as fp:
        r = csv.DictReader(fp)
        fields = r.fieldnames or []
        if a.time_col not in fields:
            print(f"[오류] 없는 열: {a.time_col} (있는 열: {fields})")
            sys.exit(1)
        for ln, row in enumerate(r, start=2):
            total += 1
            try:
                t = datetime.fromisoformat(row[a.time_col].strip())
            except ValueError:
                reason = "시각 형식 오류"
            else:
                if t.date().isoformat() in hol:
                    reason = "휴장일"
                elif t.weekday() >= 5:
                    reason = "주말"
                elif t.time() < op:
                    reason = "장 시작 전"
                elif t.time() > cl:
                    reason = "장 마감 후"
                else:
                    continue
            flagged.append({"줄": ln, "사유": reason, **row})

    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.DictWriter(fp, fieldnames=["줄", "사유"] + fields)
        w.writeheader()
        w.writerows(flagged)
    print(f"전체 {total}건 중 장 시간 밖 {len(flagged)}건 → {a.output}")


if __name__ == "__main__":
    main()
