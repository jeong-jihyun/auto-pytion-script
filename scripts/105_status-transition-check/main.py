"""주문·전표 같은 건의 '상태 변경 이력'이 허용된 순서대로 바뀌었는지 검사하는 스크립트.

생각의 흐름:
  1) 허용 규칙(JSON): 각 상태에서 갈 수 있는 다음 상태 목록. 예) 접수 → [승인, 취소]
  2) 이력 CSV(건번호, 변경일시, 상태)를 건별로 모아 시간순으로 정렬합니다.
  3) 앞 상태 → 뒤 상태가 규칙에 없으면 '허용 안 된 전이'(예: 접수 → 완료, 승인 단계를 건너뜀).
  4) 첫 상태가 시작 상태가 아니거나, 끝 상태(완료·취소) 다음에 또 바뀌면 표시합니다.
  5) 끝 상태에 도달하지 못하고 오래 머문 건(--stale-days)은 '정체'로 표시합니다.
  ERP·주문 시스템의 데이터 정합성 점검, 테스트 데이터 검증에 씁니다.
"""
import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description="상태 전이 이력 검사")
    p.add_argument("history", type=Path, help="CSV(건번호,변경일시,상태)")
    p.add_argument("--rules", type=Path, default=Path(__file__).with_name("sample") / "rules.json")
    p.add_argument("--today", default=datetime.now().strftime("%Y-%m-%d %H:%M"))
    p.add_argument("--stale-days", type=float, default=7)
    p.add_argument("-o", "--output", type=Path, default=Path("output/transition_check.csv"))
    a = p.parse_args()

    rules = json.loads(a.rules.read_text(encoding="utf-8"))
    allowed = {k: set(v) for k, v in rules["transitions"].items()}
    start, final = set(rules["start"]), set(rules["final"])
    now = datetime.strptime(a.today, "%Y-%m-%d %H:%M")
    hist = defaultdict(list)
    with a.history.open(newline="", encoding="utf-8-sig") as fp:
        for r in csv.DictReader(fp):
            hist[r["건번호"].strip()].append((datetime.strptime(r["변경일시"].strip(), "%Y-%m-%d %H:%M"), r["상태"].strip()))

    out, bad = [], 0
    for key, items in hist.items():
        items.sort()
        path = [s for _, s in items]
        probs = []
        if path[0] not in start:
            probs.append(f"시작 상태 아님({path[0]})")
        for (t1, s1), (t2, s2) in zip(items, items[1:]):
            if s1 in final:
                probs.append(f"끝난 뒤 변경({s1}→{s2})")
            elif s2 not in allowed.get(s1, set()):
                probs.append(f"허용 안 된 전이({s1}→{s2})")
            if s1 not in allowed and s1 not in final:
                probs.append(f"규칙에 없는 상태({s1})")
        last_t, last_s = items[-1]
        if last_s not in final and (now - last_t).total_seconds() > a.stale_days * 86400:
            probs.append(f"정체({(now - last_t).days}일째 {last_s})")
        if probs:
            bad += 1
        out.append([key, " → ".join(path), last_s, "정상" if not probs else "확인 필요", " / ".join(dict.fromkeys(probs))])
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["건번호", "상태경로", "현재상태", "결과", "문제"])
        w.writerows(out)
    print(f"{len(out)}건 중 확인 필요 {bad}건 → {a.output}")
    for r in out:
        if r[3] != "정상":
            print(f"  - {r[0]} [{r[1]}]: {r[4]}")


if __name__ == "__main__":
    main()
