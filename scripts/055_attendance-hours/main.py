"""출퇴근 기록 CSV로 일별 근무시간·초과근무·지각을 계산하는 스크립트.

입력 열: 사번, 이름, 날짜, 출근, 퇴근  (시간은 09:05 형식)
- 근무시간 = (퇴근 - 출근) - 점심시간(기본 60분, 4시간 미만 근무면 빼지 않음)
- 초과근무 = 근무시간 - 기준시간(기본 8시간)  (0보다 클 때만)
- 지각 = 출근이 기준 출근시각(기본 09:00)보다 늦은 경우
퇴근이 출근보다 이르면 다음 날 퇴근(야간 근무)으로 봅니다.
"""
import argparse
import csv
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def minutes(hhmm):
    t = datetime.strptime(hhmm.strip(), "%H:%M")
    return t.hour * 60 + t.minute


def hm(mins):
    return f"{mins // 60}:{mins % 60:02d}"


def main():
    p = argparse.ArgumentParser(description="근태(근무시간) 집계")
    p.add_argument("input", type=Path)
    p.add_argument("--lunch", type=int, default=60, help="점심시간(분)")
    p.add_argument("--standard", type=int, default=480, help="하루 기준 근무(분)")
    p.add_argument("--start", default="09:00", help="기준 출근시각")
    p.add_argument("-o", "--output-dir", type=Path, default=Path("output"))
    a = p.parse_args()

    daily, problems = [], []
    with a.input.open(newline="", encoding="utf-8-sig") as fp:
        for n, row in enumerate(csv.DictReader(fp), start=2):
            try:
                s, e = minutes(row["출근"]), minutes(row["퇴근"])
            except (ValueError, KeyError):
                problems.append(f"{n}번 줄: 출퇴근 시간을 읽을 수 없음 ({row})")
                continue
            if e < s:
                e += 24 * 60                       # 야간 근무
            span = e - s
            work = span - (a.lunch if span >= 240 else 0)
            over = max(0, work - a.standard)
            late = s > minutes(a.start)
            daily.append([row["사번"], row["이름"], row["날짜"], row["출근"], row["퇴근"],
                          work, over, "지각" if late else ""])

    a.output_dir.mkdir(parents=True, exist_ok=True)
    with (a.output_dir / "daily.csv").open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["사번", "이름", "날짜", "출근", "퇴근", "근무(분)", "초과(분)", "지각"])
        w.writerows(daily)

    total = defaultdict(lambda: [0, 0, 0, 0, ""])   # 사번 -> 일수, 근무분, 초과분, 지각수, 이름
    for emp, name, _, _, _, work, over, late in daily:
        t = total[emp]
        t[0] += 1; t[1] += work; t[2] += over; t[3] += 1 if late else 0; t[4] = name
    with (a.output_dir / "summary.csv").open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["사번", "이름", "근무일수", "총근무(시:분)", "총초과(시:분)", "지각횟수"])
        for emp, t in sorted(total.items()):
            w.writerow([emp, t[4], t[0], hm(t[1]), hm(t[2]), t[3]])
            print(f"  {emp} {t[4]}: {t[0]}일, 총 {hm(t[1])}, 초과 {hm(t[2])}, 지각 {t[3]}회")
    print(f"[완료] {len(daily)}건 계산 -> {a.output_dir}/daily.csv, summary.csv")
    for msg in problems:
        print("[확인 필요]", msg)


if __name__ == "__main__":
    main()
