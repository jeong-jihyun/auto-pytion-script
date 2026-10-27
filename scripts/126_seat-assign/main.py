"""교육·워크숍 참석자를 부서가 고르게 섞이도록 테이블(조)에 배정하는 스크립트.

생각의 흐름:
  1) 조를 짤 때 같은 부서끼리 몰리면 교류가 안 됩니다. 손으로 섞으면 시간이 오래 걸리고 불공평해 보입니다.
  2) 참석자를 부서별로 묶고, 사람이 많은 부서부터 한 명씩 테이블에 나눠 앉힙니다.
     한 명을 앉힐 때는 '그 부서 사람이 가장 적은 테이블' → 그중 '사람이 가장 적은 테이블'을 고릅니다.
     이렇게 하면 부서도 섞이고 테이블 인원도 고르게 됩니다.
  3) 같은 부서 안 순서는 무작위로 섞되, --seed 값을 기록해 두면 언제든 같은 결과를 다시 만들 수 있습니다.
  4) 테이블 수 × 좌석 수보다 사람이 많으면 시작하기 전에 알려 줍니다.
  5) 테이블별 명단과, 테이블마다 같은 부서가 최대 몇 명인지 점검표를 만듭니다.
"""
import argparse
import csv
import math
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description="부서가 섞이게 테이블(조) 배정")
    p.add_argument("people", type=Path, help="CSV(이름,부서)")
    p.add_argument("--tables", type=int, help="테이블 수(없으면 --seats로 자동 계산)")
    p.add_argument("--seats", type=int, default=6, help="테이블당 최대 좌석(기본 6)")
    p.add_argument("--seed", type=int, default=2026, help="무작위 기준값(같으면 같은 결과)")
    p.add_argument("-o", "--outdir", type=Path, default=Path("output"))
    a = p.parse_args()

    by_dept = defaultdict(list)
    with a.people.open(newline="", encoding="utf-8-sig") as fp:
        for r in csv.DictReader(fp):
            if r["이름"].strip():
                by_dept[r["부서"].strip() or "(부서없음)"].append(r["이름"].strip())
    total = sum(len(v) for v in by_dept.values())
    tables = a.tables or math.ceil(total / a.seats)
    if total > tables * a.seats:
        sys.exit(f"자리가 모자랍니다: 참석 {total}명 > 테이블 {tables}개 × {a.seats}석 = {tables * a.seats}석")

    rng = random.Random(a.seed)
    seat = [[] for _ in range(tables)]
    dept_count = [Counter() for _ in range(tables)]
    order = list(range(tables))
    rng.shuffle(order)  # 동점일 때 1번 테이블만 먼저 차지 않도록 순서도 섞음
    for dept in sorted(by_dept, key=lambda d: (-len(by_dept[d]), d)):
        names = by_dept[dept][:]
        rng.shuffle(names)
        for name in names:
            free = [t for t in order if len(seat[t]) < a.seats]
            t = min(free, key=lambda t: (dept_count[t][dept], len(seat[t])))
            seat[t].append((name, dept))
            dept_count[t][dept] += 1

    a.outdir.mkdir(parents=True, exist_ok=True)
    with (a.outdir / "seating.csv").open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["테이블", "좌석", "이름", "부서"])
        for t in range(tables):
            for s, (name, dept) in enumerate(seat[t], start=1):
                w.writerow([t + 1, s, name, dept])
    # 이론상 최소값: 부서 인원 ÷ 테이블 수 (올림). 실제 최대가 이보다 크면 더 섞을 수 있다는 뜻
    print(f"참석 {total}명, 부서 {len(by_dept)}개 → 테이블 {tables}개(최대 {a.seats}석), seed={a.seed}")
    for t in range(tables):
        top_dept, top_n = dept_count[t].most_common(1)[0] if seat[t] else ("-", 0)
        names = ", ".join(f"{n}({d})" for n, d in seat[t])
        print(f"  {t + 1}번 테이블 {len(seat[t])}명 | 같은 부서 최대 {top_n}명({top_dept}) | {names}")
    worst = max(max(c.values(), default=0) for c in dept_count)
    best = max(math.ceil(len(v) / tables) for v in by_dept.values())
    print(f"점검: 한 테이블 같은 부서 최대 {worst}명 (이론상 최소 {best}명) -> {a.outdir}/seating.csv")


if __name__ == "__main__":
    main()
