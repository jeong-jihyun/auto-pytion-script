"""CSV를 마크다운 표로 바꾸는 스크립트. 보고서·위키·깃허브 README에 표를 붙여 넣을 때 씁니다.

한글은 화면에서 폭이 2칸이라, 표가 정렬되어 보이도록 글자 폭을 계산해 칸을 맞춥니다.
숫자 열은 오른쪽 정렬(---:)로 표시합니다.
"""
import argparse
import csv
import sys
import unicodedata
from pathlib import Path


def width(s):
    """화면 폭(한글·전각은 2칸)."""
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)


def pad(s, w, right=False):
    gap = " " * (w - width(s))
    return gap + s if right else s + gap


def is_number(s):
    try:
        float(s.replace(",", ""))
        return True
    except ValueError:
        return False


def main():
    p = argparse.ArgumentParser(description="CSV → 마크다운 표")
    p.add_argument("input", type=Path)
    p.add_argument("-o", "--output", type=Path, default=Path("output/table.md"))
    p.add_argument("--max-rows", type=int, default=0, help="앞쪽 N행만(0이면 전부)")
    a = p.parse_args()

    with a.input.open(newline="", encoding="utf-8-sig") as fp:
        rows = list(csv.reader(fp))
    if not rows:
        print("[오류] 빈 파일입니다.")
        sys.exit(1)
    head, body = rows[0], rows[1:]
    if a.max_rows:
        body = body[: a.max_rows]
    n = len(head)
    # 칸 수가 모자란 행은 빈칸으로 채우고, '|' 글자는 깨지지 않게 바꿉니다.
    body = [[c.replace("|", "\\|") for c in (r + [""] * n)[:n]] for r in body]
    head = [c.replace("|", "\\|") for c in head]
    ws = [max([3, width(head[i])] + [width(r[i]) for r in body]) for i in range(n)]
    right = [bool(body) and all(is_number(r[i]) for r in body if r[i]) and any(r[i] for r in body) for i in range(n)]

    lines = ["| " + " | ".join(pad(head[i], ws[i]) for i in range(n)) + " |"]
    lines.append("| " + " | ".join(("-" * (ws[i] - 1) + ":") if right[i] else "-" * ws[i] for i in range(n)) + " |")
    for r in body:
        lines.append("| " + " | ".join(pad(r[i], ws[i], right[i]) for i in range(n)) + " |")

    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{len(body)}행 {n}열 표를 만들었습니다 → {a.output}")


if __name__ == "__main__":
    main()
