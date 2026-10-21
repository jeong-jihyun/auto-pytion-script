"""폴더 파일 목록(인벤토리) 만들기 스크립트.

폴더 안의 모든 파일(하위 폴더 포함)의 경로·이름·확장자·크기·수정일을 CSV 한 장으로 만들고,
확장자별 개수와 크기 합계를 화면에 보여 줍니다. 파일은 읽기만 하고 바꾸지 않습니다.
"""
import argparse
import csv
import time
from collections import defaultdict
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description="폴더 파일 목록 CSV 만들기")
    p.add_argument("folder", type=Path)
    p.add_argument("-o", "--output", type=Path, default=Path("output/inventory.csv"))
    a = p.parse_args()
    if not a.folder.is_dir():
        raise SystemExit(f"오류: 폴더가 아닙니다: {a.folder}")

    a.output.parent.mkdir(parents=True, exist_ok=True)
    out_abs = a.output.resolve()
    stat = defaultdict(lambda: [0, 0])  # 확장자 -> [개수, 크기합]
    count = 0
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["상대경로", "파일이름", "확장자", "크기(바이트)", "수정일시"])
        for f in sorted(a.folder.rglob("*")):
            if not f.is_file() or f.resolve() == out_abs:
                continue
            st = f.stat()
            ext = f.suffix.lower() or "(없음)"
            mtime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(st.st_mtime))
            w.writerow([f.relative_to(a.folder).as_posix(), f.name, ext, st.st_size, mtime])
            stat[ext][0] += 1
            stat[ext][1] += st.st_size
            count += 1
    print(f"파일 {count}개 -> {a.output}")
    for ext, (n, size) in sorted(stat.items(), key=lambda x: -x[1][1]):
        print(f"  {ext:10s} {n:4d}개  {size:10d}바이트")


if __name__ == "__main__":
    main()
