"""요청 접수~처리 완료까지 걸린 '업무시간'을 계산하고 SLA(목표 시간) 초과 건을 찾는 스크립트.

업무시간: 평일 09:00~18:00(옵션으로 변경), 점심시간(12~13시)은 제외, 주말·휴일 제외.
예) 금요일 17:00 접수 → 월요일 10:00 완료 = 업무시간 2시간.
"""
import argparse
import csv
import sys
from datetime import datetime, timedelta, time
from pathlib import Path


def load_holidays(path):
    """휴일 파일(한 줄에 YYYY-MM-DD)을 읽습니다."""
    if not path:
        return set()
    return {x.strip() for x in path.read_text(encoding="utf-8-sig").splitlines() if x.strip() and not x.startswith("#")}


def business_minutes(start, end, ws, we, lunch, holidays):
    """start~end 사이의 업무 분(分)을 날짜별로 더합니다."""
    if end <= start:
        return 0
    total = 0
    day = start.date()
    while day <= end.date():
        if day.weekday() < 5 and day.isoformat() not in holidays:
            # 하루의 업무 구간: (오전) ws~점심시작, (오후) 점심끝~we
            for a, b in ((ws, lunch[0]), (lunch[1], we)):
                seg_s = max(start, datetime.combine(day, a))
                seg_e = min(end, datetime.combine(day, b))
                if seg_e > seg_s:
                    total += int((seg_e - seg_s).total_seconds() // 60)
        day += timedelta(days=1)
    return total


def parse_time(s):
    h, m = s.split(":")
    return time(int(h), int(m))


def main():
    p = argparse.ArgumentParser(description="업무시간 기준 SLA 점검")
    p.add_argument("input", type=Path)
    p.add_argument("--start-col", default="접수시각")
    p.add_argument("--end-col", default="완료시각")
    p.add_argument("--sla-hours", type=float, default=8, help="목표 업무시간(시간)")
    p.add_argument("--work-start", default="09:00")
    p.add_argument("--work-end", default="18:00")
    p.add_argument("--lunch", default="12:00-13:00")
    p.add_argument("--holidays", type=Path, help="휴일 목록 파일")
    p.add_argument("-o", "--output", type=Path, default=Path("output/sla.csv"))
    a = p.parse_args()

    ws, we = parse_time(a.work_start), parse_time(a.work_end)
    l1, l2 = a.lunch.split("-")
    lunch = (parse_time(l1), parse_time(l2))
    hol = load_holidays(a.holidays)
    out, over, bad = [], 0, 0
    with a.input.open(newline="", encoding="utf-8-sig") as fp:
        r = csv.DictReader(fp)
        fields = r.fieldnames or []
        for need in (a.start_col, a.end_col):
            if need not in fields:
                print(f"[오류] 없는 열: {need} (있는 열: {fields})")
                sys.exit(1)
        for row in r:
            try:
                s = datetime.fromisoformat(row[a.start_col].strip())
                e = datetime.fromisoformat(row[a.end_col].strip())
            except ValueError:
                row["업무시간(시간)"], row["SLA"] = "", "시각 형식 오류"
                bad += 1
                out.append(row)
                continue
            h = business_minutes(s, e, ws, we, lunch, hol) / 60
            row["업무시간(시간)"] = f"{h:.2f}"
            row["SLA"] = "초과" if h > a.sla_hours else "충족"
            over += row["SLA"] == "초과"
            out.append(row)

    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.DictWriter(fp, fieldnames=fields + ["업무시간(시간)", "SLA"])
        w.writeheader()
        w.writerows(out)
    print(f"{len(out)}건 중 SLA 초과 {over}건, 형식 오류 {bad}건 → {a.output}")


if __name__ == "__main__":
    main()
