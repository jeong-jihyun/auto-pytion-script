"""직원 명단 CSV(사번, 상사 사번)로 조직도 트리를 그리고, 명단의 잘못된 곳을 찾아 주는 스크립트.

생각의 흐름:
  1) 인사 명단에는 보통 '내 상사의 사번' 한 칸만 있습니다. 이걸로 위에서 아래로 내려가는 트리를 만들 수 있습니다.
  2) 상사 사번이 비어 있는 사람이 맨 위(대표·본부장)입니다. 여러 명이면 트리가 여러 개 생깁니다.
  3) 명단이 틀리면 트리가 이상해집니다. 그래서 먼저 검사합니다.
     - 같은 사번이 두 번 나옴
     - 상사 사번이 명단에 없음(퇴사자를 상사로 둔 경우 등)
     - 자기 자신이 상사
     - 순환(A의 상사가 B, B의 상사가 A) → 이 사람들은 맨 위로 올라갈 수 없어서 트리에 안 나옵니다.
  4) 관리 폭(직속 부하 수)이 너무 많거나(기본 8명 초과) 조직 깊이가 너무 깊은(기본 5단계 초과) 곳도 알려 줍니다.
  5) 결과는 화면용 텍스트 트리와 마크다운 파일로 저장합니다.
"""
import argparse
import csv
import os
import sys
from collections import defaultdict


def load(path, id_col, boss_col):
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for c in (id_col, boss_col):
            if c not in (reader.fieldnames or []):
                sys.exit(f"[오류] '{c}' 열이 없습니다. 있는 열: {reader.fieldnames}")
        return list(reader)


def main():
    ap = argparse.ArgumentParser(description="직원 명단으로 조직도 트리 만들기 + 명단 검사")
    ap.add_argument("input", help="직원 명단 CSV")
    ap.add_argument("--id-col", default="사번")
    ap.add_argument("--boss-col", default="상사사번")
    ap.add_argument("--label", default="이름,직급,부서", help="트리에 보여줄 열(쉼표 구분)")
    ap.add_argument("--max-span", type=int, default=8, help="직속 부하가 이보다 많으면 알림 (기본 8)")
    ap.add_argument("--max-depth", type=int, default=5, help="단계가 이보다 깊으면 알림 (기본 5)")
    ap.add_argument("--output", default="output/org_chart.md")
    args = ap.parse_args()

    rows = load(args.input, args.id_col, args.boss_col)
    label_cols = [c.strip() for c in args.label.split(",") if c.strip()]
    issues = []

    people, seen = {}, set()
    for i, r in enumerate(rows, start=2):
        pid = r[args.id_col].strip()
        if not pid:
            issues.append(f"{i}행: 사번이 비어 있음")
            continue
        if pid in seen:
            issues.append(f"{i}행: 사번 {pid} 가 중복됨(첫 번째 것만 사용)")
            continue
        seen.add(pid)
        people[pid] = r

    children, roots = defaultdict(list), []
    for pid, r in people.items():
        boss = r[args.boss_col].strip()
        if not boss:
            roots.append(pid)
        elif boss == pid:
            issues.append(f"사번 {pid}: 자기 자신이 상사로 적혀 있음")
        elif boss not in people:
            issues.append(f"사번 {pid}: 상사 사번 {boss} 가 명단에 없음 → 맨 위로 따로 표시")
            roots.append(pid)
        else:
            children[boss].append(pid)

    def label(pid):
        r = people[pid]
        parts = [r.get(c, "").strip() for c in label_cols if r.get(c, "").strip()]
        return f"{' / '.join(parts)} ({pid})"

    lines, placed, max_seen = [], set(), 0

    def walk(pid, prefix, last, depth):
        nonlocal max_seen
        placed.add(pid)
        max_seen = max(max_seen, depth)
        kids = sorted(children.get(pid, []))
        branch = "" if depth == 1 else ("└─ " if last else "├─ ")
        lines.append(f"{prefix}{branch}{label(pid)}" + (f"  [직속 {len(kids)}명]" if kids else ""))
        if len(kids) > args.max_span:
            issues.append(f"사번 {pid}: 직속 부하 {len(kids)}명 (기준 {args.max_span}명 초과)")
        if depth > args.max_depth:
            issues.append(f"사번 {pid}: {depth}단계 (기준 {args.max_depth}단계 초과)")
        child_prefix = prefix if depth == 1 else prefix + ("   " if last else "│  ")
        for k, kid in enumerate(kids):
            walk(kid, child_prefix, k == len(kids) - 1, depth + 1)

    for root in sorted(roots):
        walk(root, "", True, 1)
        lines.append("")

    # 트리에 한 번도 안 나온 사람 = 순환 참조에 걸린 사람
    lost = sorted(set(people) - placed)
    if lost:
        issues.append("순환 참조로 트리에 넣을 수 없는 사번: " + ", ".join(lost))

    out = ["# 조직도", "", f"인원 {len(people)}명 · 최상위 {len(roots)}명 · 최대 {max_seen}단계", "",
           "```", *lines, "```", "", "## 확인할 점"]
    out += [f"- {x}" for x in issues] if issues else ["- 없음"]

    d = os.path.dirname(args.output)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")

    print("\n".join(lines).rstrip())
    print("-" * 40)
    print(f"인원 {len(people)}명, 최상위 {len(roots)}명, 최대 {max_seen}단계")
    print("확인할 점:" if issues else "확인할 점: 없음")
    for x in issues:
        print(f"  - {x}")
    print(f"저장: {args.output}")


if __name__ == "__main__":
    main()
