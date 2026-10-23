"""기념일·만기일 목록에서 오늘 기준 D-day 를 계산하는 스크립트.

입력 CSV 열: 이름, 날짜(YYYY-MM-DD), 종류(선택: 매년/한번)
- 종류가 '매년'이면(생일·입사기념일) 올해 날짜로 바꿔서 이미 지났으면 내년으로 계산합니다.
- 종류가 '한번'(또는 비어 있음)이면(계약 만기 등) 입력한 날짜 그대로 계산합니다. 이미 지났으면 '지남' 표시.
- --within N: 앞으로 N일 안에 있는 것만 보여줍니다. --today 로 기준일을 바꿀 수 있습니다(테스트용).
2월 29일 생일은 평년에는 2월 28일로 계산합니다.
"""
import argparse
import csv
from datetime import date, datetime
from pathlib import Path


def next_occurrence(d: date, today: date) -> date:
    """매년 반복되는 날짜의 '오늘 이후 가장 가까운 날'을 구합니다."""
    def in_year(y):
        try:
            return d.replace(year=y)
        except ValueError:          # 2/29 -> 평년
            return date(y, 2, 28)
    this_year = in_year(today.year)
    return this_year if this_year >= today else in_year(today.year + 1)


def main():
    p = argparse.ArgumentParser(description="기념일·만기일 D-day 계산")
    p.add_argument("input", type=Path)
    p.add_argument("--today", help="기준일 YYYY-MM-DD (기본: 오늘)")
    p.add_argument("--within", type=int, help="앞으로 N일 이내만 표시")
    p.add_argument("-o", "--output", type=Path, default=Path("output/dday.csv"))
    a = p.parse_args()

    today = datetime.strptime(a.today, "%Y-%m-%d").date() if a.today else date.today()
    result, bad = [], 0
    with a.input.open(newline="", encoding="utf-8-sig") as fp:
        for row in csv.DictReader(fp):
            try:
                d = datetime.strptime(row["날짜"].strip(), "%Y-%m-%d").date()
            except (ValueError, KeyError):
                bad += 1
                print(f"[건너뜀] 날짜를 읽을 수 없는 행: {row}")
                continue
            kind = (row.get("종류") or "한번").strip()
            target = next_occurrence(d, today) if kind == "매년" else d
            left = (target - today).days
            if a.within is not None and not (0 <= left <= a.within):
                continue
            label = "D-DAY" if left == 0 else (f"D-{left}" if left > 0 else f"지남({-left}일)")
            result.append([row["이름"], kind, target.isoformat(), left, label])
    result.sort(key=lambda x: (x[3] < 0, abs(x[3])))   # 다가오는 순서, 지난 것은 뒤로

    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["이름", "종류", "대상일", "남은일수", "표시"])
        w.writerows(result)
    print(f"기준일 {today}, {len(result)}건 (읽기 실패 {bad}건) -> {a.output}")
    for r in result:
        print(f"  {r[4]:>10}  {r[0]}  ({r[2]})")


if __name__ == "__main__":
    main()
