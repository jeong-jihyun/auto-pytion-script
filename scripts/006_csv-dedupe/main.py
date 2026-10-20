"""CSV 중복 제거 스크립트.

지정한 열(들)이 같으면 중복으로 보고, 첫 번째 행만 남깁니다.
중복으로 걸러진 행은 별도 파일(removed)로 저장해서 눈으로 확인할 수 있습니다.
원본 파일은 수정하지 않습니다.
"""
import argparse
import csv
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description="CSV 중복 제거")
    p.add_argument("input", type=Path)
    p.add_argument("--keys", required=True, help="중복 기준 열 이름 (쉼표로 여러 개)")
    p.add_argument("-o", "--output", type=Path, default=Path("output"))
    a = p.parse_args()
    keys = [k.strip() for k in a.keys.split(",")]
    seen, keep, removed = set(), [], []
    with a.input.open(newline="", encoding="utf-8-sig") as fp:
        r = csv.DictReader(fp)
        header = r.fieldnames
        for k in keys:
            if k not in header:
                raise SystemExit(f"오류: '{k}' 열이 없습니다. 열 목록: {header}")
        for row in r:
            # 앞뒤 공백·대소문자 차이는 같은 값으로 봅니다
            sig = tuple(row[k].strip().lower() for k in keys)
            (removed if sig in seen else keep).append(row)
            seen.add(sig)
    a.output.mkdir(parents=True, exist_ok=True)
    for name, rows in (("deduped.csv", keep), ("removed.csv", removed)):
        with (a.output / name).open("w", newline="", encoding="utf-8-sig") as fp:
            w = csv.DictWriter(fp, fieldnames=header)
            w.writeheader()
            w.writerows(rows)
    print(f"전체 {len(keep)+len(removed)}행 -> 남김 {len(keep)}행, 제거 {len(removed)}행")


if __name__ == "__main__":
    main()
