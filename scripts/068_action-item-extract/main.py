"""회의록 텍스트에서 '할 일(액션 아이템)'을 뽑아 표로 만드는 스크립트.

인식하는 줄 모양(예):
  - [ ] 견적서 보내기 @김가나 ~10/30
  TODO: 서버 점검 (담당: 이다라, 기한: 2026-11-02)
  액션: 보고서 초안 작성 / 담당 박마바 / 기한 11/05
담당자·기한은 있으면 뽑고, 없으면 빈칸으로 둡니다. 날짜가 'MM/DD'면 --year 연도를 붙입니다.
"""
import argparse
import csv
import re
import sys
from datetime import date
from pathlib import Path

START = re.compile(r"^\s*(?:[-*]\s*\[ \]\s*|TODO\s*[:：]\s*|액션\s*[:：]\s*|할\s*일\s*[:：]\s*)(.+)$", re.I)
OWNER = re.compile(r"(?:@|담당\s*[:：]?\s*)([가-힣A-Za-z]{2,10})")
DUE = re.compile(r"(?:~|기한\s*[:：]?\s*)(\d{4}-\d{1,2}-\d{1,2}|\d{1,2}/\d{1,2})")


def to_date(s, year):
    """'2026-11-02' 또는 '11/05' 를 YYYY-MM-DD로. 잘못된 날짜면 원문 그대로."""
    try:
        if "-" in s:
            y, m, d = map(int, s.split("-"))
        else:
            m, d = map(int, s.split("/"))
            y = year
        return date(y, m, d).isoformat()
    except ValueError:
        return s


def main():
    p = argparse.ArgumentParser(description="회의록 액션 아이템 추출")
    p.add_argument("input", type=Path, help="회의록 텍스트 파일 또는 폴더")
    p.add_argument("--year", type=int, default=date.today().year)
    p.add_argument("-o", "--output", type=Path, default=Path("output/actions.csv"))
    a = p.parse_args()

    files = sorted(a.input.glob("*.txt")) + sorted(a.input.glob("*.md")) if a.input.is_dir() else [a.input]
    if not files or not all(f.is_file() for f in files):
        print(f"[오류] 읽을 파일이 없습니다: {a.input}")
        sys.exit(1)

    out = []
    for f in files:
        for ln, line in enumerate(f.read_text(encoding="utf-8-sig").splitlines(), start=1):
            m = START.match(line)
            if not m:
                continue
            body = m.group(1)
            owner = OWNER.search(body)
            due = DUE.search(body)
            # 담당·기한 표시를 뺀 나머지가 할 일 내용
            task = DUE.sub("", OWNER.sub("", body))
            task = re.sub(r"[()/／]|담당|기한", " ", task)
            task = re.sub(r"\s+", " ", task).strip(" ,:-")
            out.append({"파일": f.name, "줄": ln, "할 일": task,
                        "담당": owner.group(1) if owner else "",
                        "기한": to_date(due.group(1), a.year) if due else ""})

    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.DictWriter(fp, fieldnames=["파일", "줄", "할 일", "담당", "기한"])
        w.writeheader()
        w.writerows(out)
    nodue = sum(1 for x in out if not x["기한"])
    print(f"할 일 {len(out)}건 추출 (기한 없음 {nodue}건) → {a.output}")


if __name__ == "__main__":
    main()
