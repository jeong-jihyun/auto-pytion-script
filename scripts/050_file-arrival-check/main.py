"""매일 들어와야 하는 파일이 제때 도착했는지 점검하는 스크립트 (배치 전 점검용).

기대 목록(JSON)에 '파일 이름 패턴'을 적어 두면 폴더에서 찾아 아래를 점검합니다.
  - 없음(MISSING)  - 크기 0(EMPTY)  - 너무 작음(SMALL: min_bytes 미만)
  - 너무 오래됨(STALE: max_age_hours 보다 예전에 수정됨)  - 정상(OK)
패턴에는 {date:%Y%m%d} 처럼 오늘 날짜를 넣을 수 있습니다. --today 로 기준일을 바꿀 수 있습니다.
문제가 하나라도 있으면 종료 코드 1 을 돌려줘서 다른 배치와 이어 쓰기 좋습니다.
"""
import argparse
import csv
import fnmatch
import json
import sys
from datetime import datetime
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description="필수 파일 도착 점검")
    p.add_argument("folder", type=Path, help="파일이 들어오는 폴더")
    p.add_argument("--rules", required=True, type=Path, help="기대 목록 JSON")
    p.add_argument("--today", help="기준일 YYYY-MM-DD (기본: 오늘)")
    p.add_argument("--now", help="현재 시각 YYYY-MM-DD HH:MM (STALE 계산용, 기본: 지금)")
    p.add_argument("-o", "--output", type=Path, default=Path("output/arrival.csv"))
    a = p.parse_args()

    rules = json.loads(a.rules.read_text(encoding="utf-8"))
    today = datetime.strptime(a.today, "%Y-%m-%d") if a.today else datetime.now()
    now = datetime.strptime(a.now, "%Y-%m-%d %H:%M") if a.now else datetime.now()
    files = [f for f in a.folder.iterdir() if f.is_file()]

    rows, problems = [], 0
    for rule in rules:
        pattern = rule["pattern"].format(date=today)
        matched = [f for f in files if fnmatch.fnmatch(f.name, pattern)]
        if not matched:
            status, name, size, age = "MISSING", "", "", ""
        else:
            f = max(matched, key=lambda x: x.stat().st_mtime)     # 여러 개면 가장 최근 것
            size = f.stat().st_size
            age = round((now - datetime.fromtimestamp(f.stat().st_mtime)).total_seconds() / 3600, 1)
            name = f.name
            if size == 0:
                status = "EMPTY"
            elif size < rule.get("min_bytes", 0):
                status = "SMALL"
            elif "max_age_hours" in rule and age > rule["max_age_hours"]:
                status = "STALE"
            else:
                status = "OK"
        if status != "OK":
            problems += 1
        rows.append([rule.get("label", pattern), pattern, status, name, size, age])

    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["항목", "찾은 패턴", "상태", "파일", "크기(byte)", "수정후경과(시간)"])
        w.writerows(rows)
    print(f"기준일 {today:%Y-%m-%d} / 점검 {len(rows)}개 / 문제 {problems}개 -> {a.output}")
    for r in rows:
        print(f"  [{r[2]:7}] {r[0]}  {r[3]}")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
