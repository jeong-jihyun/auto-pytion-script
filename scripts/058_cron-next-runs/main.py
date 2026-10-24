"""크론(cron) 표현식이 언제 실행되는지 미리 계산해 보는 스크립트.

5칸 형식: 분 시 일 월 요일  (예: '30 2 * * 1-5' = 평일 새벽 2시 30분)
지원: 숫자, *, 범위(1-5), 목록(1,15), 간격(*/10, 0-30/5). 요일은 0 또는 7이 일요일.
일(日)과 요일을 둘 다 지정하면 표준 크론처럼 '둘 중 하나라도 맞으면' 실행으로 봅니다.
배치 스케줄이 겹치거나 빠졌는지 점검할 때 씁니다. 실제로 작업을 실행하지는 않습니다.
"""
import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

RANGES = [(0, 59), (0, 23), (1, 31), (1, 12), (0, 7)]
NAMES = ["분", "시", "일", "월", "요일"]


def parse_field(text, lo, hi):
    """한 칸을 허용되는 숫자 집합으로 바꿉니다."""
    out = set()
    for part in text.split(","):
        step = 1
        if "/" in part:
            part, s = part.split("/")
            step = int(s)
            if step < 1:
                raise ValueError("간격은 1 이상")
        if part == "*":
            a, b = lo, hi
        elif "-" in part:
            a, b = (int(x) for x in part.split("-"))
        else:
            a = int(part)
            b = hi if step > 1 else a
        if a < lo or b > hi or a > b:
            raise ValueError(f"범위 밖: {text}")
        out.update(range(a, b + 1, step))
    return out


def parse(expr):
    parts = expr.split()
    if len(parts) != 5:
        raise ValueError("5칸이어야 합니다(분 시 일 월 요일)")
    sets = []
    for i, part in enumerate(parts):
        try:
            sets.append(parse_field(part, *RANGES[i]))
        except ValueError as exc:
            raise ValueError(f"{NAMES[i]} 칸 오류: {exc}")
    sets[4] = {d % 7 for d in sets[4]}           # 7 -> 0 (일요일)
    return sets, parts[2] != "*", parts[4] != "*"


def day_ok(dt, sets, dom_given, dow_given):
    dow = (dt.weekday() + 1) % 7                 # 월=1 ... 일=0
    dom_hit, dow_hit = dt.day in sets[2], dow in sets[4]
    if dom_given and dow_given:
        return dom_hit or dow_hit
    return dom_hit and dow_hit


def next_runs(expr, start, count):
    sets, dom_given, dow_given = parse(expr)
    t = start.replace(second=0, microsecond=0) + timedelta(minutes=1)
    limit = start + timedelta(days=366 * 5)
    found = []
    while len(found) < count and t < limit:
        if t.month not in sets[3]:
            t = (t.replace(day=1, hour=0, minute=0) + timedelta(days=32)).replace(day=1)
        elif not day_ok(t, sets, dom_given, dow_given):
            t = t.replace(hour=0, minute=0) + timedelta(days=1)
        elif t.hour not in sets[1]:
            t = t.replace(minute=0) + timedelta(hours=1)
        elif t.minute not in sets[0]:
            t += timedelta(minutes=1)
        else:
            found.append(t)
            t += timedelta(minutes=1)
    return found


def main():
    p = argparse.ArgumentParser(description="크론 표현식 다음 실행 시각 계산")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--expr", help="예: '30 2 * * 1-5'")
    g.add_argument("--file", type=Path, help="'이름|표현식' 형식의 줄 목록 파일")
    p.add_argument("--from", dest="start", default=None, help="기준 시각 'YYYY-MM-DD HH:MM' (기본: 지금)")
    p.add_argument("-n", "--count", type=int, default=5, help="몇 번 보여 줄지")
    a = p.parse_args()

    start = datetime.strptime(a.start, "%Y-%m-%d %H:%M") if a.start else datetime.now()
    jobs = []
    if a.expr:
        jobs.append(("(직접 입력)", a.expr))
    else:
        for line in a.file.read_text(encoding="utf-8").splitlines():
            if line.strip() and not line.startswith("#"):
                name, _, expr = line.partition("|")
                jobs.append((name.strip(), expr.strip()))

    bad = 0
    print(f"[기준 시각] {start:%Y-%m-%d %H:%M} 이후")
    for name, expr in jobs:
        try:
            runs = next_runs(expr, start, a.count)
        except ValueError as exc:
            print(f"- {name} [{expr}] -> 오류: {exc}")
            bad += 1
            continue
        times = ", ".join(f"{r:%m-%d(%a) %H:%M}" for r in runs) or "(5년 안에 실행 없음)"
        print(f"- {name} [{expr}] -> {times}")
    if bad:
        sys.exit(1)


if __name__ == "__main__":
    main()
