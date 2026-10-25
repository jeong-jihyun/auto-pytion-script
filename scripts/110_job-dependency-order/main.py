"""배치 작업들의 선후관계(이 작업은 저 작업이 끝나야 시작)를 보고 실행 순서와 문제를 찾는 스크립트.

생각의 흐름:
  1) 작업 CSV(작업ID, 선행작업, 예상분)를 읽습니다. 선행작업이 여러 개면 ; 로 구분합니다.
  2) 위상 정렬(Kahn 방식): 선행작업이 없는 작업부터 꺼내고, 꺼낸 작업을 기다리던 작업의
     '남은 선행 수'를 하나씩 줄입니다. 0이 되면 실행 가능한 상태가 됩니다.
     같은 단계에서 함께 꺼낼 수 있는 작업들은 '동시에 돌릴 수 있는 묶음'(단계)입니다.
  3) 끝까지 꺼내지 못한 작업이 남으면 서로가 서로를 기다리는 '순환 의존'입니다.
  4) 정의되지 않은 선행작업(오타 등)도 찾아 줍니다.
  5) 예상 시간이 있으면 가장 오래 걸리는 경로(임계 경로)와 전체 예상 종료 시간을 계산합니다.
"""
import argparse
import csv
from collections import defaultdict
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description="배치 작업 선후관계 실행 순서 계산")
    p.add_argument("jobs", type=Path, help="CSV(작업ID,선행작업,예상분)")
    p.add_argument("-o", "--output", type=Path, default=Path("output/job_order.csv"))
    a = p.parse_args()

    deps, minutes, order_in_file = {}, {}, []
    with a.jobs.open(newline="", encoding="utf-8-sig") as fp:
        for r in csv.DictReader(fp):
            j = r["작업ID"].strip()
            order_in_file.append(j)
            deps[j] = [x.strip() for x in (r.get("선행작업") or "").split(";") if x.strip()]
            minutes[j] = float(r.get("예상분") or 0)
    unknown = sorted({(j, d) for j, ds in deps.items() for d in ds if d not in deps})
    for j, d in unknown:
        deps[j].remove(d)  # 없는 작업은 무시하고 계속(경고로 알림)

    remain = {j: len(ds) for j, ds in deps.items()}
    waiting = defaultdict(list)
    for j, ds in deps.items():
        for d in ds:
            waiting[d].append(j)
    stage_of, finish, via = {}, {}, {}
    ready = [j for j in order_in_file if remain[j] == 0]
    stage = 0
    while ready:
        stage += 1
        nxt = []
        for j in ready:
            stage_of[j] = stage
            start = max((finish[d] for d in deps[j]), default=0)
            via[j] = max(deps[j], key=lambda d: finish[d]) if deps[j] else None
            finish[j] = start + minutes[j]
            for w in waiting[j]:
                remain[w] -= 1
                if remain[w] == 0:
                    nxt.append(w)
        ready = sorted(nxt, key=order_in_file.index)
    cycle = [j for j in order_in_file if j not in stage_of]

    rows = sorted(stage_of, key=lambda j: (stage_of[j], order_in_file.index(j)))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["단계", "작업ID", "선행작업", "예상분", "예상시작(분)", "예상종료(분)"])
        for j in rows:
            w.writerow([stage_of[j], j, ";".join(deps[j]), minutes[j], finish[j] - minutes[j], finish[j]])
        for j in cycle:
            w.writerow(["순환", j, ";".join(deps[j]), minutes[j], "", ""])
    print(f"작업 {len(deps)}개 → {stage}단계로 실행 가능 {len(rows)}개 → {a.output}")
    for s in range(1, stage + 1):
        print(f"  {s}단계(동시 실행 가능): {', '.join(j for j in rows if stage_of[j] == s)}")
    if finish:
        end = max(finish, key=finish.get)
        path, cur = [], end
        while cur:
            path.append(cur)
            cur = via[cur]
        print(f"  임계 경로: {' → '.join(reversed(path))} (전체 예상 {finish[end]:g}분)")
    if cycle:
        print(f"  ! 순환 의존(서로 기다림)으로 실행 못 하는 작업: {', '.join(cycle)}")
    for j, d in unknown:
        print(f"  ! {j}의 선행작업 '{d}' 가 목록에 없음(오타 확인)")


if __name__ == "__main__":
    main()
