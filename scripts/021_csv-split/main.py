"""CSV 나누기 스크립트.

큰 CSV 파일을 두 가지 방법으로 나눕니다.
  1) --rows N  : N행씩 잘라서 part_001.csv, part_002.csv ... 로 저장
  2) --by 열이름 : 그 열의 값이 같은 행끼리 모아서 값별 파일로 저장 (예: 지점별)
모든 파일에 머리글(첫 줄)을 똑같이 붙입니다. 원본은 수정하지 않습니다.
"""
import argparse
import csv
import re
from pathlib import Path


def safe_name(text):
    """파일 이름으로 쓸 수 없는 글자를 _ 로 바꿉니다."""
    text = re.sub(r'[\\/:*?"<>|\s]+', "_", text.strip())
    return text or "빈값"


def write_csv(path, header, rows):
    with path.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(header)
        w.writerows(rows)


def main():
    p = argparse.ArgumentParser(description="CSV 나누기")
    p.add_argument("input", type=Path, help="나눌 CSV 파일")
    p.add_argument("-o", "--output", type=Path, default=Path("output"))
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--rows", type=int, help="파일 하나에 담을 행 수")
    g.add_argument("--by", help="이 열의 값별로 나눔")
    a = p.parse_args()

    with a.input.open(newline="", encoding="utf-8-sig") as fp:
        r = csv.reader(fp)
        header = next(r, None)
        if header is None:
            raise SystemExit("오류: 빈 파일입니다.")
        rows = list(r)
    a.output.mkdir(parents=True, exist_ok=True)

    if a.rows:
        if a.rows < 1:
            raise SystemExit("오류: --rows 는 1 이상이어야 합니다.")
        n = 0
        for i in range(0, len(rows), a.rows):
            n += 1
            write_csv(a.output / f"part_{n:03d}.csv", header, rows[i:i + a.rows])
        print(f"{len(rows)}행 -> {n}개 파일 ({a.rows}행씩)")
    else:
        if a.by not in header:
            raise SystemExit(f"오류: '{a.by}' 열이 없습니다. 열 목록: {header}")
        idx = header.index(a.by)
        groups = {}
        for row in rows:
            key = row[idx] if idx < len(row) else ""
            groups.setdefault(key, []).append(row)
        used = set()
        for key, grp in groups.items():
            name = safe_name(key)
            while name in used:  # 이름이 겹치면 번호를 붙여 구분
                name += "_"
            used.add(name)
            write_csv(a.output / f"{a.by}_{name}.csv", header, grp)
            print(f"  {key or '(빈값)'}: {len(grp)}행")
        print(f"{len(rows)}행 -> {len(groups)}개 파일 ({a.by} 값별)")


if __name__ == "__main__":
    main()
