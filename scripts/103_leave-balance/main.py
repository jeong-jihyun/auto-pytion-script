"""연차(휴가) 사용 내역으로 사람별 사용 일수와 남은 연차를 계산하는 스크립트.

생각의 흐름:
  1) 부여 파일(이름, 부여일수, 이월일수)과 사용 내역(이름, 시작일, 종료일, 구분)을 읽습니다.
  2) 사용 일수 계산: 시작~종료 중 '평일'만 셉니다(주말·휴일 제외).
     구분이 반차면 0.5일, 반반차면 0.25일로 셉니다.
  3) 남은 연차 = 부여 + 이월 - 사용. 음수면 '초과 사용', 기준일까지 남은 연차가 많으면 '사용 촉진 대상'.
  4) 같은 사람이 같은 날 두 번 신청한 건(중복 신청)도 찾아 줍니다.
"""
import argparse
import csv
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

UNIT = {"연차": 1.0, "반차": 0.5, "오전반차": 0.5, "오후반차": 0.5, "반반차": 0.25}


def days(start, end, holidays):
    d, out = start, []
    while d <= end:
        if d.weekday() < 5 and d.isoformat() not in holidays:
            out.append(d)
        d += timedelta(days=1)
    return out


def main():
    p = argparse.ArgumentParser(description="연차 사용·잔여 계산")
    p.add_argument("grants", type=Path, help="CSV(이름,부여일수,이월일수)")
    p.add_argument("usage", type=Path, help="CSV(이름,시작일,종료일,구분)")
    p.add_argument("--holidays", default="", help="휴일(쉼표)")
    p.add_argument("--promote", type=float, default=5, help="남은 연차가 이 이상이면 사용 촉진 대상")
    p.add_argument("-o", "--output", type=Path, default=Path("output/leave_balance.csv"))
    a = p.parse_args()

    hol = {x.strip() for x in a.holidays.split(",") if x.strip()}
    grants = {}
    with a.grants.open(newline="", encoding="utf-8-sig") as fp:
        for r in csv.DictReader(fp):
            grants[r["이름"].strip()] = float(r["부여일수"] or 0) + float(r.get("이월일수") or 0)
    used = defaultdict(float)
    seen = defaultdict(list)
    warnings = []
    with a.usage.open(newline="", encoding="utf-8-sig") as fp:
        for r in csv.DictReader(fp):
            name = r["이름"].strip()
            kind = (r.get("구분") or "연차").strip()
            unit = UNIT.get(kind)
            if unit is None:
                warnings.append(f"{name} {r['시작일']}: 모르는 구분 '{kind}' → 1일로 계산")
                unit = 1.0
            s = date.fromisoformat(r["시작일"].strip())
            e = date.fromisoformat((r.get("종료일") or r["시작일"]).strip())
            for d in days(s, e, hol):
                if seen[(name, d)] and sum(seen[(name, d)]) + unit > 1:
                    warnings.append(f"{name} {d}: 같은 날 중복 신청")
                seen[(name, d)].append(unit)
                used[name] += unit
            if name not in grants:
                warnings.append(f"{name}: 부여 파일에 없는 사람")

    rows = []
    for name in list(grants) + [n for n in used if n not in grants]:
        g = grants.get(name, 0)
        left = g - used[name]
        state = "초과 사용" if left < 0 else ("사용 촉진 대상" if left >= a.promote else "정상")
        rows.append([name, g, used[name], left, state])
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["이름", "부여(이월포함)", "사용", "잔여", "상태"])
        w.writerows(rows)
    print(f"{len(rows)}명 연차 계산 → {a.output}")
    for r in rows:
        print(f"  - {r[0]}: 부여 {r[1]:g} / 사용 {r[2]:g} / 잔여 {r[3]:g} ({r[4]})")
    for x in warnings:
        print(f"  ! {x}")


if __name__ == "__main__":
    main()
