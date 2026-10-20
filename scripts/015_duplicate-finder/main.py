"""중복 파일 찾기 스크립트.

폴더 안(하위 폴더 포함)에서 '내용이 똑같은' 파일을 찾아 보고서(CSV)로 만듭니다.
- 이름이 달라도 내용이 같으면 중복, 이름이 같아도 내용이 다르면 중복이 아닙니다.
- 빠르게 하려고 먼저 크기가 같은 파일만 골라서 sha256 해시를 비교합니다.
- 기본은 보고서만 만듭니다. 중복을 옮기고 싶으면 --move-to 폴더 와 --apply 를 함께 쓰세요.
  (삭제는 하지 않고 '옮기기'만 합니다. 마음이 바뀌면 되돌릴 수 있게요.)
"""
import argparse
import csv
import hashlib
import shutil
import sys
from collections import defaultdict
from pathlib import Path


def 해시(경로, 조각크기=1024 * 1024):
    h = hashlib.sha256()
    with 경로.open("rb") as fp:
        while True:
            덩어리 = fp.read(조각크기)
            if not 덩어리:
                break
            h.update(덩어리)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser(description="내용이 같은 중복 파일 찾기")
    p.add_argument("input", help="검사할 폴더")
    p.add_argument("-o", "--output", default="output/duplicates.csv", help="보고서 CSV 경로")
    p.add_argument("--min-size", type=int, default=1, help="이 바이트 이상인 파일만 검사 (기본 1)")
    p.add_argument("--move-to", help="중복 파일을 옮겨 둘 폴더 (선택)")
    p.add_argument("--apply", action="store_true", help="--move-to 를 실제로 실행 (없으면 미리보기)")
    a = p.parse_args()

    루트 = Path(a.input)
    if not 루트.is_dir():
        print(f"폴더가 아닙니다: {루트}")
        return 1
    옮길곳 = Path(a.move_to).resolve() if a.move_to else None
    크기별 = defaultdict(list)
    for f in sorted(루트.rglob("*")):
        if f.is_file() and not f.is_symlink() and f.stat().st_size >= a.min_size:
            if 옮길곳 and 옮길곳 in f.resolve().parents:
                continue  # 이미 옮겨 둔 폴더는 다시 검사하지 않음
            크기별[f.stat().st_size].append(f)

    그룹들 = []
    for 크기, 후보 in 크기별.items():
        if len(후보) < 2:
            continue
        해시별 = defaultdict(list)
        for f in 후보:
            해시별[해시(f)].append(f)
        그룹들 += [(크기, hs, fs) for hs, fs in 해시별.items() if len(fs) > 1]

    out = Path(a.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    낭비 = 0
    옮길목록 = []
    with out.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["그룹", "구분", "파일", "크기(바이트)"])
        for n, (크기, hs, fs) in enumerate(sorted(그룹들, key=lambda g: g[2][0].as_posix()), start=1):
            # 수정 시각이 가장 오래된 파일 1개(같은 초면 이름순)를 '유지'로 표시하고 나머지를 '중복'으로 봅니다.
            fs = sorted(fs, key=lambda f: (int(f.stat().st_mtime), f.as_posix()))
            for i, f in enumerate(fs):
                w.writerow([n, "유지" if i == 0 else "중복", f.as_posix(), 크기])
                if i > 0:
                    낭비 += 크기
                    옮길목록.append(f)
    print(f"완료: 중복 그룹 {len(그룹들)}개, 중복 파일 {len(옮길목록)}개, 낭비 {낭비:,} 바이트 -> {out}")

    if 옮길곳 and 옮길목록:
        if not a.apply:
            print("[미리보기] 아래 파일을 옮길 예정입니다. 실제로 옮기려면 --apply 를 붙이세요.")
        else:
            옮길곳.mkdir(parents=True, exist_ok=True)
        for f in 옮길목록:
            대상 = 옮길곳 / f.relative_to(루트)
            print(f"  {f.as_posix()} -> {대상.as_posix()}")
            if a.apply:
                대상.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(f), str(대상))
    return 0


if __name__ == "__main__":
    sys.exit(main())
