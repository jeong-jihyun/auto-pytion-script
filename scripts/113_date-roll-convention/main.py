"""지급일·결제일이 주말이나 휴일이면 규칙에 따라 영업일로 옮겨 주는 스크립트.

생각의 흐름:
  1) 이자 지급일, 카드 결제일, 급여일은 '매월 25일'처럼 정해지지만 그날이 휴일일 수 있습니다.
  2) 금융에서 많이 쓰는 4가지 규칙이 있습니다.
     - following(익영업일): 다음 영업일로 미룸
     - preceding(전영업일): 앞 영업일로 당김
     - modified_following(수정익영업일): 미루되, 달이 바뀌면 대신 앞으로 당김
     - modified_preceding(수정전영업일): 당기되, 달이 바뀌면 대신 뒤로 미룸
  3) 날짜 목록 CSV(이름,날짜)와 휴일 파일을 읽어, 규칙별로 옮긴 날짜를 한 표로 보여 줍니다.
"""
import argparse
import csv
from datetime import date, timedelta
from pathlib import Path

RULES = ["following", "preceding", "modified_following", "modified_preceding"]


def is_bd(d, holidays):
    return d.weekday() < 5 and d not in holidays


def step(d, holidays, delta):
    """영업일이 될 때까지 delta(+1/-1)일씩 움직입니다."""
    while not is_bd(d, holidays):
        d += timedelta(days=delta)
    return d


def roll(d, rule, holidays):
    if rule == "following":
        return step(d, holidays, 1)
    if rule == "preceding":
        return step(d, holidays, -1)
    if rule == "modified_following":
        n = step(d, holidays, 1)
        return n if n.month == d.month else step(d, holidays, -1)
    if rule == "modified_preceding":
        n = step(d, holidays, -1)
        return n if n.month == d.month else step(d, holidays, 1)
    raise ValueError(rule)


def load_holidays(path):
    if not path:
        return set()
    out = set()
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.split("#")[0].strip()
        if line:
            out.add(date.fromisoformat(line[:10]))
    return out


def main():
    p = argparse.ArgumentParser(description="휴일 날짜 조정(영업일 규칙)")
    p.add_argument("dates", type=Path, help="CSV(이름,날짜 YYYY-MM-DD)")
    p.add_argument("--holidays", type=Path, help="휴일 파일(한 줄에 날짜 하나, # 뒤는 메모)")
    p.add_argument("--rule", choices=RULES, help="한 가지 규칙만 볼 때")
    p.add_argument("-o", "--output", type=Path, default=Path("output/rolled_dates.csv"))
    a = p.parse_args()

    hol = load_holidays(a.holidays)
    rules = [a.rule] if a.rule else RULES
    week = "월화수목금토일"
    rows = []
    with a.dates.open(newline="", encoding="utf-8-sig") as fp:
        for r in csv.DictReader(fp):
            d = date.fromisoformat(r["날짜"].strip())
            row = [r["이름"], d.isoformat(), week[d.weekday()], "예" if is_bd(d, hol) else "아니오"]
            for rule in rules:
                n = roll(d, rule, hol)
                row.append(f"{n.isoformat()}({week[n.weekday()]})")
            rows.append(row)

    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["이름", "원래날짜", "요일", "영업일여부"] + rules)
        w.writerows(rows)
    moved = sum(1 for r in rows if r[3] == "아니오")
    print(f"날짜 {len(rows)}개 중 휴일·주말이라 옮겨야 하는 날짜 {moved}개 → {a.output}")
    for r in rows:
        if r[3] == "아니오":
            print("  " + " | ".join(r))


if __name__ == "__main__":
    main()
