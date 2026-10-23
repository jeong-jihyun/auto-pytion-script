"""전표·주문·계약 번호에서 '빠진 번호'와 '중복 번호'를 찾는 스크립트.

번호는 'INV-2026-0001' 처럼 앞글자(접두어) + 숫자 형태여야 합니다.
접두어가 다르면 그룹으로 나눠서 따로 검사합니다. 숫자가 이어져야 하는 일련번호 점검에 씁니다.
"""
import argparse
import csv
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path


def split_no(text):
    """'INV-2026-0001' -> ('INV-2026-', 1, 4)  (접두어, 숫자값, 숫자 자릿수)"""
    m = re.match(r"^(.*?)(\d+)$", text.strip())
    if not m:
        return None
    return m.group(1), int(m.group(2)), len(m.group(2))


def main():
    p = argparse.ArgumentParser(description="일련번호 누락·중복 찾기")
    p.add_argument("input", type=Path, help="CSV 파일")
    p.add_argument("--column", required=True, help="번호가 들어 있는 열 이름")
    p.add_argument("-o", "--output", type=Path, default=Path("output/gaps.csv"))
    a = p.parse_args()

    with a.input.open(newline="", encoding="utf-8-sig") as fp:
        r = csv.DictReader(fp)
        if a.column not in (r.fieldnames or []):
            print(f"[오류] 없는 열: {a.column} (있는 열: {r.fieldnames})")
            sys.exit(1)
        values = [row[a.column] for row in r]

    groups = defaultdict(list)   # 접두어 -> [(숫자, 자릿수)]
    unreadable = []
    for v in values:
        s = split_no(v)
        if s is None:
            unreadable.append(v)
        else:
            groups[s[0]].append((s[1], s[2]))

    report = []  # (구분, 접두어, 번호)
    for prefix, items in sorted(groups.items()):
        nums = [n for n, _ in items]
        width = max(w for _, w in items)
        cnt = Counter(nums)
        for n, c in sorted(cnt.items()):
            if c > 1:
                report.append(("중복", prefix, f"{prefix}{n:0{width}d} ({c}번 나옴)"))
        have = set(nums)
        for n in range(min(nums), max(nums) + 1):
            if n not in have:
                report.append(("누락", prefix, f"{prefix}{n:0{width}d}"))
        print(f"[{prefix or '(접두어 없음)'}] {min(nums)}~{max(nums)} / 실제 {len(have)}개 / 범위 {max(nums)-min(nums)+1}개")
    for v in unreadable:
        report.append(("형식오류", "", v))

    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["구분", "접두어", "번호"])
        w.writerows(report)
    miss = sum(1 for x in report if x[0] == "누락")
    dup = sum(1 for x in report if x[0] == "중복")
    print(f"누락 {miss}건, 중복 {dup}건, 형식오류 {len(unreadable)}건 -> {a.output}")
    for row in report:
        print("  ", *row)


if __name__ == "__main__":
    main()
