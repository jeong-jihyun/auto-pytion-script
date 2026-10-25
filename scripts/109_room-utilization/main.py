"""회의실·차량·장비 예약 내역으로 자원별 '사용률'과 붐비는 시간대를 계산하는 스크립트.

생각의 흐름:
  1) 예약 CSV(자원, 시작, 종료, 상태)를 읽고 취소된 예약은 뺍니다.
  2) 예약 시간을 '업무시간(예: 09~18시) 안'으로 잘라 냅니다. 업무시간 밖은 사용률에 넣지 않습니다.
  3) 같은 자원의 예약이 겹치면 합쳐서 두 번 세지 않게 합니다(구간 병합).
  4) 사용률 = 예약된 업무시간 ÷ (기간 중 평일 수 × 하루 업무시간).
  5) 시간대(9시, 10시, …)별로 '몇 개 자원이 쓰였는지' 세어 가장 붐비는 시간을 알려 줍니다.
  → 회의실이 모자란지, 남는지 판단하는 근거 자료가 됩니다.
"""
import argparse
import csv
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from pathlib import Path

FMT = "%Y-%m-%d %H:%M"


def merge(iv):
    out = []
    for s, e in sorted(iv):
        if out and s <= out[-1][1]:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return out


def main():
    p = argparse.ArgumentParser(description="예약 자원 사용률 집계")
    p.add_argument("bookings", type=Path, help="CSV(자원,시작,종료,상태)")
    p.add_argument("--start", required=True, help="기간 시작 YYYY-MM-DD")
    p.add_argument("--end", required=True, help="기간 끝 YYYY-MM-DD")
    p.add_argument("--work", default="09:00-18:00")
    p.add_argument("-o", "--outdir", type=Path, default=Path("output"))
    a = p.parse_args()

    ws, we = [time.fromisoformat(x) for x in a.work.split("-")]
    d0, d1 = date.fromisoformat(a.start), date.fromisoformat(a.end)
    workdays = [d0 + timedelta(i) for i in range((d1 - d0).days + 1) if (d0 + timedelta(i)).weekday() < 5]
    day_hours = (datetime.combine(d0, we) - datetime.combine(d0, ws)).total_seconds() / 3600
    per_res = defaultdict(list)
    resources = set()
    with a.bookings.open(newline="", encoding="utf-8-sig") as fp:
        for r in csv.DictReader(fp):
            resources.add(r["자원"].strip())
            if (r.get("상태") or "").strip() == "취소":
                continue
            s, e = datetime.strptime(r["시작"].strip(), FMT), datetime.strptime(r["종료"].strip(), FMT)
            for d in workdays:  # 업무시간 안으로 잘라서 날짜별로 넣기
                cs, ce = max(s, datetime.combine(d, ws)), min(e, datetime.combine(d, we))
                if cs < ce:
                    per_res[r["자원"].strip()].append((cs, ce))

    hour_busy = defaultdict(set)
    rows = []
    cap = len(workdays) * day_hours
    for res in sorted(resources):
        merged = merge(per_res.get(res, []))
        used = sum((e - s).total_seconds() for s, e in merged) / 3600
        for s, e in merged:
            t = s.replace(minute=0)
            while t < e:
                hour_busy[t.hour].add((res, t.date()))
                t += timedelta(hours=1)
        rows.append([res, round(used, 1), round(cap, 1), round(used / cap * 100, 1) if cap else 0])
    rows.sort(key=lambda x: -x[3])
    a.outdir.mkdir(parents=True, exist_ok=True)
    with (a.outdir / "utilization.csv").open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["자원", "사용시간", "가능시간", "사용률%"])
        w.writerows(rows)
    with (a.outdir / "by_hour.csv").open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["시각", "평균 사용 자원 수", "자원 수", "혼잡도%"])
        for h in range(ws.hour, we.hour + (1 if we.minute else 0)):
            avg = len(hour_busy[h]) / len(workdays) if workdays else 0
            w.writerow([f"{h:02d}시", round(avg, 2), len(resources), round(avg / len(resources) * 100, 1) if resources else 0])
    print(f"평일 {len(workdays)}일, 자원 {len(resources)}개 → {a.outdir / 'utilization.csv'}, {a.outdir / 'by_hour.csv'}")
    for r in rows:
        print(f"  - {r[0]}: 사용률 {r[3]}% ({r[1]}h / {r[2]}h)")
    if hour_busy:
        peak = max(hour_busy, key=lambda h: len(hour_busy[h]))
        print(f"  가장 붐비는 시간: {peak:02d}시 (평균 {len(hour_busy[peak]) / len(workdays):.2f}개 사용)")


if __name__ == "__main__":
    main()
