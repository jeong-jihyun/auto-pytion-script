"""여러 사람의 '바쁜 시간' 목록을 모아, 모두가 비어 있는 회의 가능 시간을 찾는 스크립트.

생각의 흐름:
  1) 일정 CSV(이름,시작,종료)에서 참석자들의 바쁜 구간만 모읍니다.
  2) 날짜마다 업무시간(예: 09:00~18:00)과 점심시간을 정하고, 점심도 '바쁨'으로 봅니다.
  3) 바쁜 구간들을 시간순으로 정렬하고 겹치는 것을 합칩니다. (구간 병합)
  4) 업무시간에서 합친 바쁜 구간을 빼면 남는 것이 '모두 빈 시간'입니다.
  5) 회의 길이(--minutes)보다 짧은 틈은 버리고, 앞에서부터 후보를 보여 줍니다.
"""
import argparse
import csv
from datetime import date, datetime, time, timedelta
from pathlib import Path

FMT = "%Y-%m-%d %H:%M"


def hm(s):
    h, m = s.split(":")
    return time(int(h), int(m))


def merge(intervals):
    out = []
    for s, e in sorted(intervals):
        if out and s <= out[-1][1]:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return out


def main():
    p = argparse.ArgumentParser(description="모두 비어 있는 회의 시간 찾기")
    p.add_argument("busy", type=Path, help="일정 CSV(이름,시작,종료) 시각 형식 2026-10-27 10:00")
    p.add_argument("--people", default="", help="참석자 이름(쉼표). 비우면 파일의 모든 사람")
    p.add_argument("--start", required=True, help="찾기 시작 날짜 YYYY-MM-DD")
    p.add_argument("--days", type=int, default=5, help="며칠 동안 찾을지(주말 제외)")
    p.add_argument("--minutes", type=int, default=60, help="회의 길이(분)")
    p.add_argument("--work", default="09:00-18:00", help="업무시간")
    p.add_argument("--lunch", default="12:00-13:00", help="점심시간(없으면 빈칸)")
    p.add_argument("--top", type=int, default=10, help="보여 줄 후보 수")
    p.add_argument("-o", "--output", type=Path, default=Path("output/free_slots.csv"))
    a = p.parse_args()

    wanted = {x.strip() for x in a.people.split(",") if x.strip()}
    busy, seen = [], set()
    with a.busy.open(newline="", encoding="utf-8-sig") as fp:
        for r in csv.DictReader(fp):
            name = r["이름"].strip()
            seen.add(name)
            if wanted and name not in wanted:
                continue
            busy.append((datetime.strptime(r["시작"].strip(), FMT), datetime.strptime(r["종료"].strip(), FMT)))
    missing = wanted - seen
    if missing:
        print(f"  ! 일정 파일에 없는 사람(바쁜 일정 없음으로 처리): {', '.join(sorted(missing))}")

    ws, we = [hm(x) for x in a.work.split("-")]
    lunch = [hm(x) for x in a.lunch.split("-")] if a.lunch else None
    need = timedelta(minutes=a.minutes)
    d = date.fromisoformat(a.start)
    slots, counted = [], 0
    while counted < a.days:
        if d.weekday() < 5:
            counted += 1
            day_s, day_e = datetime.combine(d, ws), datetime.combine(d, we)
            todays = [(max(s, day_s), min(e, day_e)) for s, e in busy if s < day_e and e > day_s]
            if lunch:
                todays.append((datetime.combine(d, lunch[0]), datetime.combine(d, lunch[1])))
            cur = day_s
            for s, e in merge(todays):
                if s - cur >= need:
                    slots.append((cur, s))
                cur = max(cur, e)
            if day_e - cur >= need:
                slots.append((cur, day_e))
        d += timedelta(days=1)

    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["날짜", "요일", "빈시간시작", "빈시간종료", "길이(분)"])
        for s, e in slots:
            w.writerow([s.date(), "월화수목금토일"[s.weekday()], s.strftime("%H:%M"), e.strftime("%H:%M"),
                        int((e - s).total_seconds() // 60)])
    who = ", ".join(sorted(wanted)) if wanted else f"전원({len(seen)}명)"
    print(f"참석자 {who} / {a.minutes}분 이상 빈 시간 {len(slots)}개 → {a.output}")
    for s, e in slots[:a.top]:
        print(f"  - {s:%m-%d}({'월화수목금토일'[s.weekday()]}) {s:%H:%M}~{e:%H:%M}")


if __name__ == "__main__":
    main()
