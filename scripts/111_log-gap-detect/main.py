"""로그가 한동안 안 찍힌 '공백 구간'을 찾는 스크립트.

생각의 흐름:
  1) 오류 로그가 없다고 안심하면 안 됩니다. 프로그램이 멈추면 로그 자체가 끊깁니다.
     그래서 '로그 줄 사이 시간 간격'이 기준(분)보다 긴 곳을 찾습니다.
  2) 각 줄 맨 앞의 시각(YYYY-MM-DD HH:MM:SS)을 읽습니다. 시각이 없는 줄(스택트레이스 등)은 건너뜁니다.
  3) 업무 시간(--window 09:00-18:00)을 주면, 공백이 그 시간대와 겹치는 부분만 셉니다.
     밤에 원래 조용한 시스템이면 밤 공백은 문제가 아니기 때문입니다.
  4) 결과를 CSV로 저장하고, 가장 긴 공백을 화면에 보여 줍니다.
"""
import argparse
import csv
import re
from datetime import datetime, timedelta, time
from pathlib import Path

TS = re.compile(r"^\[?(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2})")


def read_times(paths):
    """여러 로그 파일에서 시각만 모아 정렬해 돌려줍니다."""
    times = []
    for p in paths:
        with p.open(encoding="utf-8", errors="replace") as fp:
            for line in fp:
                m = TS.match(line)
                if m:
                    times.append(datetime.fromisoformat(m.group(1).replace("T", " ")))
    return sorted(times)


def overlap_minutes(start, end, win):
    """start~end 중 매일 업무시간(win)과 겹치는 분을 계산합니다. win이 없으면 전체."""
    if not win:
        return (end - start).total_seconds() / 60
    total, day = 0.0, start.date()
    while day <= end.date():
        ws, we = datetime.combine(day, win[0]), datetime.combine(day, win[1])
        s, e = max(start, ws), min(end, we)
        if e > s:
            total += (e - s).total_seconds() / 60
        day += timedelta(days=1)
    return total


def main():
    p = argparse.ArgumentParser(description="로그 공백 구간 탐지")
    p.add_argument("logs", nargs="+", type=Path, help="로그 파일(여러 개 가능)")
    p.add_argument("--gap", type=float, default=10, help="이 분 이상 비면 공백으로 봄(기본 10)")
    p.add_argument("--window", help="업무 시간만 볼 때 예: 09:00-18:00")
    p.add_argument("-o", "--output", type=Path, default=Path("output/log_gaps.csv"))
    a = p.parse_args()

    win = None
    if a.window:
        s, e = a.window.split("-")
        win = (time.fromisoformat(s), time.fromisoformat(e))

    times = read_times(a.logs)
    if len(times) < 2:
        print("시각이 있는 로그 줄이 2줄 미만이라 비교할 수 없습니다.")
        return
    rows = []
    for prev, cur in zip(times, times[1:]):
        mins = overlap_minutes(prev, cur, win)
        if mins >= a.gap:
            rows.append([prev, cur, round((cur - prev).total_seconds() / 60, 1), round(mins, 1)])

    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["공백시작(마지막로그)", "공백끝(다음로그)", "전체공백분", "업무시간내공백분"])
        w.writerows(rows)

    print(f"로그 줄(시각 있음) {len(times)}개, 범위 {times[0]} ~ {times[-1]}")
    print(f"{a.gap:g}분 이상 공백 {len(rows)}건 → {a.output}")
    for r in sorted(rows, key=lambda r: -r[3])[:5]:
        print(f"  {r[0]} → {r[1]}  업무시간내 {r[3]}분 (전체 {r[2]}분)")


if __name__ == "__main__":
    main()
