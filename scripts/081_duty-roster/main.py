"""당직·당번(청소, 모니터링 당번 등) 순번표를 공평하게 자동으로 만드는 스크립트.

생각의 흐름:
  1) 사람 목록(이름, 안되는 날짜)과 기간을 받습니다. 주말·휴일은 기본으로 건너뜁니다.
  2) 날마다 필요한 인원(--per-day)을 고를 때 아래 순서로 '가장 덜 한 사람'을 고릅니다.
     ① 그날 안 되는 사람은 뺍니다.
     ② 바로 전날 한 사람은 되도록 뺍니다(연속 당번 방지). 사람이 모자라면 어쩔 수 없이 넣습니다.
     ③ 지금까지 횟수가 적은 사람 → 마지막으로 한 날이 오래된 사람 → 명단 순서
  3) 결과 순번표와 사람별 횟수를 저장합니다. 횟수 차이가 1 이하이면 '공평'으로 봅니다.
  같은 입력이면 항상 같은 결과가 나옵니다(무작위 없음).
"""
import argparse
import csv
from datetime import date, timedelta
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description="당번 순번표 자동 생성")
    p.add_argument("people", type=Path, help="사람 CSV(이름,안되는날) 안되는날은 ; 로 구분")
    p.add_argument("--start", required=True, help="시작일 YYYY-MM-DD")
    p.add_argument("--end", required=True, help="종료일 YYYY-MM-DD")
    p.add_argument("--per-day", type=int, default=1, help="하루 필요한 인원")
    p.add_argument("--holidays", default="", help="휴일(쉼표, YYYY-MM-DD)")
    p.add_argument("--include-weekend", action="store_true", help="주말도 포함")
    p.add_argument("-o", "--output", type=Path, default=Path("output/roster.csv"))
    a = p.parse_args()

    people, blocked = [], {}
    with a.people.open(newline="", encoding="utf-8-sig") as fp:
        for r in csv.DictReader(fp):
            name = r["이름"].strip()
            people.append(name)
            blocked[name] = {x.strip() for x in (r.get("안되는날") or "").split(";") if x.strip()}
    holidays = {x.strip() for x in a.holidays.split(",") if x.strip()}
    count = {n: 0 for n in people}
    last = {n: date.min for n in people}
    roster, short_days = [], []
    d, end = date.fromisoformat(a.start), date.fromisoformat(a.end)
    prev = set()
    while d <= end:
        if (d.weekday() >= 5 and not a.include_weekend) or d.isoformat() in holidays:
            d += timedelta(days=1)
            continue
        free = [n for n in people if d.isoformat() not in blocked[n]]
        order = lambda n: (count[n], last[n], people.index(n))
        rested = sorted([n for n in free if n not in prev], key=order)
        tired = sorted([n for n in free if n in prev], key=order)
        pick = (rested + tired)[:a.per_day]
        note = ""
        if len(pick) < a.per_day:
            note = f"인원 부족({len(pick)}/{a.per_day})"
            short_days.append(d)
        elif any(n in prev for n in pick):
            note = "연속 배정(사람 부족)"
        for n in pick:
            count[n] += 1
            last[n] = d
        roster.append([d.isoformat(), "월화수목금토일"[d.weekday()], ", ".join(pick), note])
        prev = set(pick)
        d += timedelta(days=1)

    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["날짜", "요일", "당번", "비고"])
        w.writerows(roster)
        w.writerow([])
        w.writerow(["이름", "횟수"])
        for n in people:
            w.writerow([n, count[n]])
    gap = max(count.values()) - min(count.values()) if count else 0
    print(f"{len(roster)}일 순번표 완성 → {a.output}  (횟수 차이 {gap}{' = 공평' if gap <= 1 else ' — 안되는날 때문에 차이 발생'})")
    print("  " + ", ".join(f"{n} {c}회" for n, c in count.items()))
    if short_days:
        print(f"  ! 인원 부족한 날: {', '.join(x.isoformat() for x in short_days)}")


if __name__ == "__main__":
    main()
