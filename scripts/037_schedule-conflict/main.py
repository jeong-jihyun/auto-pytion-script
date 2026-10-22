"""일정·예약 겹침 찾기 스크립트.

회의실·차량·장비 예약표(자원, 예약자, 시작, 종료)에서 '같은 자원을 같은 시간에'
잡은 예약 쌍을 찾아 알려 줍니다. 끝나는 시각과 시작하는 시각이 딱 맞닿는 것은 겹침이 아닙니다.
시간 형식: 2026-10-22 09:00  (또는 2026-10-22T09:00)
"""
import argparse
import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def parse_time(text):
    return datetime.fromisoformat(text.strip().replace("/", "-"))


def main():
    p = argparse.ArgumentParser(description="예약 겹침 찾기")
    p.add_argument("input", type=Path, help="CSV (열: 자원,예약자,시작,종료)")
    p.add_argument("-o", "--output", type=Path, default=Path("output/conflicts.csv"))
    a = p.parse_args()

    by_res = defaultdict(list)
    with a.input.open(newline="", encoding="utf-8-sig") as fp:
        for n, row in enumerate(csv.DictReader(fp), start=2):
            try:
                s, e = parse_time(row["시작"]), parse_time(row["종료"])
            except ValueError:
                print(f"[건너뜀] {n}번째 줄 시간 형식 오류: {row['시작']} ~ {row['종료']}")
                continue
            if e <= s:
                print(f"[건너뜀] {n}번째 줄 종료가 시작보다 빠르거나 같음: {row['예약자']}")
                continue
            by_res[row["자원"].strip()].append((s, e, row["예약자"].strip(), n))

    conflicts = []
    for res, items in by_res.items():
        items.sort()
        # 시작 시각 순으로 늘어놓으면, 앞 예약의 종료가 뒤 예약의 시작보다 늦을 때 겹칩니다.
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                if items[j][0] >= items[i][1]:
                    break  # 이후 예약은 더 늦게 시작하므로 겹칠 수 없음
                conflicts.append([res, items[i][2], items[i][0], items[i][1],
                                  items[j][2], items[j][0], items[j][1]])
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["자원", "예약자A", "A시작", "A종료", "예약자B", "B시작", "B종료"])
        w.writerows(conflicts)
    print(f"자원 {len(by_res)}개 검사, 겹침 {len(conflicts)}건 -> {a.output}")
    for c in conflicts:
        print(f"  [{c[0]}] {c[1]}({c[2]:%m-%d %H:%M}~{c[3]:%H:%M}) ↔ {c[4]}({c[5]:%m-%d %H:%M}~{c[6]:%H:%M})")


if __name__ == "__main__":
    main()
