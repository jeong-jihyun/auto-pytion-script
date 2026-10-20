"""CSV 병합 스크립트.

폴더 안의 여러 CSV 파일을 하나로 합칩니다.
- 첫 번째 파일의 헤더(제목 줄)를 기준으로 삼습니다.
- 어느 파일에서 왔는지 알 수 있게 '원본파일' 열을 붙입니다.
- 표준 라이브러리만 사용합니다.
"""
import argparse
import csv
import sys
from pathlib import Path


def merge(input_dir: Path, output: Path, encoding: str) -> int:
    files = sorted(input_dir.glob("*.csv"))
    # 출력 파일이 같은 폴더에 있으면 입력으로 다시 읽지 않도록 제외
    files = [f for f in files if f.resolve() != output.resolve()]
    if not files:
        print("합칠 CSV 파일이 없습니다.")
        return 1
    header = None
    rows = []
    for f in files:
        with f.open(newline="", encoding=encoding) as fp:
            reader = csv.DictReader(fp)
            if header is None:
                header = reader.fieldnames
            elif reader.fieldnames != header:
                # 헤더가 다르면 건너뛰고 알려줍니다 (조용히 틀린 데이터를 섞지 않기 위해)
                print(f"[건너뜀] {f.name}: 헤더가 달라요 -> {reader.fieldnames}")
                continue
            for r in reader:
                r["원본파일"] = f.name
                rows.append(r)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding=encoding) as fp:
        w = csv.DictWriter(fp, fieldnames=header + ["원본파일"])
        w.writeheader()
        w.writerows(rows)
    print(f"완료: 파일 {len(files)}개, 행 {len(rows)}개 -> {output}")
    return 0


def main():
    p = argparse.ArgumentParser(description="폴더 안의 CSV들을 하나로 병합")
    p.add_argument("input_dir", type=Path, help="CSV가 들어 있는 폴더")
    p.add_argument("-o", "--output", type=Path, default=Path("output/merged.csv"))
    p.add_argument("--encoding", default="utf-8-sig", help="인코딩 (기본 utf-8-sig)")
    a = p.parse_args()
    sys.exit(merge(a.input_dir, a.output, a.encoding))


if __name__ == "__main__":
    main()
