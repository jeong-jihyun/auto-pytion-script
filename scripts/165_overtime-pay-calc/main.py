"""출퇴근 기록과 시급으로 연장·야간·휴일 근로 시간을 나누고, 가산수당을 계산하는 스크립트.

생각의 흐름:
  1) 근태 집계(근무시간)만으로는 급여 담당자가 다시 '연장 몇 시간, 야간 몇 시간'을 손으로 나눠야 합니다.
     그래서 1분 단위로 시간을 훑으며 각 분이 어떤 종류인지 셉니다. 조금 느려도 실수가 없고 이해하기 쉽습니다.
  2) 분류 기준(근로기준법 기본, 상시 5인 이상 사업장):
       - 연장: 그날 실제 일한 시간이 8시간을 넘는 부분           → 통상시급 × 1.5
       - 야간: 22:00~06:00 사이에 일한 부분(연장과 겹쳐도 따로) → 통상시급 × 0.5 가산
       - 휴일: 휴일 근로 8시간 이내 × 1.5, 8시간 초과 × 2.0
     평일 8시간 이내 기본 근무는 월급에 들어 있다고 보고 '추가로 줄 돈'만 계산합니다.
  3) 휴게시간은 '12:00-13:00;18:00-18:30' 처럼 구간으로 받아 그 분은 일한 시간에서 뺍니다.
     퇴근이 출근보다 이르면 자정을 넘긴 것으로 봅니다.
  4) 5인 미만 사업장은 가산 규정이 적용되지 않아 --small 을 주면 연장·휴일도 1.0배, 야간 가산 0으로 계산합니다.
  5) 주 40시간 초과(주 단위 연장)는 이 스크립트에서 다루지 않고 README에 적어 둡니다.
"""
import argparse
import csv
from collections import OrderedDict
from datetime import datetime, timedelta


def parse_hm(day, hm):
    return datetime.strptime(f"{day} {hm.strip()}", "%Y-%m-%d %H:%M")


def break_minutes(day, text, start):
    """휴게 구간 문자열 → 쉬는 '분' 시각들의 집합."""
    mins = set()
    for part in (text or "").split(";"):
        if "-" not in part:
            continue
        b, e = [x.strip() for x in part.split("-", 1)]
        bs, be = parse_hm(day, b), parse_hm(day, e)
        if bs < start:  # 자정 넘긴 휴게(예: 02:00-02:30)
            bs += timedelta(days=1)
            be += timedelta(days=1)
        if be <= bs:
            be += timedelta(days=1)
        t = bs
        while t < be:
            mins.add(t)
            t += timedelta(minutes=1)
    return mins


def classify(row, base_limit):
    day = row["일자"].strip()
    start = parse_hm(day, row["출근"])
    end = parse_hm(day, row["퇴근"])
    if end <= start:
        end += timedelta(days=1)
    rest = break_minutes(day, row.get("휴게", ""), start)
    holiday = (row.get("휴일") or "").strip().upper() in ("Y", "1", "예", "O")
    worked = over = night = 0
    t = start
    while t < end:
        if t not in rest:
            worked += 1
            if worked > base_limit:
                over += 1
            if t.hour >= 22 or t.hour < 6:
                night += 1
        t += timedelta(minutes=1)
    return holiday, worked, over, night


def main():
    p = argparse.ArgumentParser(description="연장·야간·휴일 근로 가산수당 계산")
    p.add_argument("input", help="근무 CSV: 사번,이름,일자,출근,퇴근,휴게,휴일,시급")
    p.add_argument("-o", "--output", default="overtime_daily.out.csv")
    p.add_argument("--summary", default="overtime_person.out.csv")
    p.add_argument("--hourly", type=float, help="시급 열이 비었을 때 쓸 통상시급")
    p.add_argument("--small", action="store_true", help="상시 5인 미만 사업장(가산 없음)")
    p.add_argument("--daily-hours", type=float, default=8, help="하루 기준 근로시간(기본 8)")
    p.add_argument("--encoding", default="utf-8-sig")
    a = p.parse_args()

    limit = int(a.daily_hours * 60)
    r_over, r_hol, r_hol_over, r_night = (1.0, 1.0, 1.0, 0.0) if a.small else (1.5, 1.5, 2.0, 0.5)

    with open(a.input, newline="", encoding=a.encoding) as f:
        rows = list(csv.DictReader(f))

    daily, people = [], OrderedDict()
    for r in rows:
        wage = float(r.get("시급") or a.hourly or 0)
        if not wage:
            print(f"  ✗ {r.get('이름')} {r.get('일자')}: 시급이 없습니다(--hourly 로 기본값을 주세요)")
            continue
        holiday, worked, over, night = classify(r, limit)
        if holiday:
            hol_in, hol_over, ot = worked - over, over, 0
        else:
            hol_in, hol_over, ot = 0, 0, over
        pay = (ot * r_over + hol_in * r_hol + hol_over * r_hol_over + night * r_night) * wage / 60
        pay = int(round(pay))
        d = OrderedDict([
            ("사번", r.get("사번", "")), ("이름", r.get("이름", "")), ("일자", r["일자"]),
            ("휴일", "Y" if holiday else ""), ("실근로(시간)", round(worked / 60, 2)),
            ("연장(시간)", round(ot / 60, 2)), ("휴일8h이내(시간)", round(hol_in / 60, 2)),
            ("휴일8h초과(시간)", round(hol_over / 60, 2)), ("야간(시간)", round(night / 60, 2)),
            ("시급", int(wage)), ("수당", pay),
        ])
        daily.append(d)
        key = (d["사번"], d["이름"])
        s = people.setdefault(key, {"일수": 0, "실근로": 0, "연장": 0, "휴일": 0, "야간": 0, "수당": 0})
        s["일수"] += 1
        s["실근로"] += worked
        s["연장"] += ot
        s["휴일"] += hol_in + hol_over
        s["야간"] += night
        s["수당"] += pay

    if daily:
        with open(a.output, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(daily[0].keys()))
            w.writeheader()
            w.writerows(daily)
    with open(a.summary, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["사번", "이름", "근무일수", "실근로(시간)", "연장(시간)", "휴일(시간)", "야간(시간)", "수당합계"])
        for (no, name), s in people.items():
            w.writerow([no, name, s["일수"], round(s["실근로"] / 60, 2), round(s["연장"] / 60, 2),
                        round(s["휴일"] / 60, 2), round(s["야간"] / 60, 2), s["수당"]])

    print(f"{'5인 미만(가산 없음)' if a.small else '5인 이상(가산 적용)'} 기준, {len(daily)}일 계산 → {a.output}, {a.summary}")
    for (no, name), s in people.items():
        print(f"  {name}: 연장 {s['연장'] / 60:g}h, 휴일 {s['휴일'] / 60:g}h, 야간 {s['야간'] / 60:g}h → 수당 {s['수당']:,}원")


if __name__ == "__main__":
    main()
