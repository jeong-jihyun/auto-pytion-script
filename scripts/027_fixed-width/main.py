"""고정길이 전문 파일 -> CSV 변환 스크립트.

은행·증권 시스템에서 주고받는 '고정길이(fixed width)' 텍스트 파일을 읽어 CSV 로 바꿉니다.
각 항목의 시작 위치와 길이는 규칙 JSON 으로 알려 줍니다. 위치와 길이는 '바이트' 기준이고
(한글은 cp949 에서 2바이트), 시작 위치는 1부터 셉니다.
규칙 예: [{"name": "종목코드", "start": 1, "length": 6}, ...]
"""
import argparse
import csv
import json
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description="고정길이 파일 -> CSV")
    p.add_argument("input", type=Path, help="고정길이 텍스트 파일")
    p.add_argument("--spec", type=Path, required=True, help="항목 규칙 JSON")
    p.add_argument("--encoding", default="cp949", help="입력 파일 인코딩 (기본 cp949)")
    p.add_argument("-o", "--output", type=Path, default=Path("output/fixed_width.csv"))
    a = p.parse_args()

    spec = json.loads(a.spec.read_text(encoding="utf-8"))
    for f in spec:
        if not {"name", "start", "length"} <= set(f) or f["start"] < 1 or f["length"] < 1:
            raise SystemExit(f"오류: 규칙이 잘못되었습니다: {f}")
    need = max(f["start"] - 1 + f["length"] for f in spec)  # 한 줄에 필요한 최소 바이트

    rows, short = [], []
    for no, raw in enumerate(a.input.read_bytes().splitlines(), start=1):
        if not raw.strip():
            continue
        if len(raw) < need:
            short.append((no, len(raw)))
        row = []
        for f in spec:
            piece = raw[f["start"] - 1:f["start"] - 1 + f["length"]]
            row.append(piece.decode(a.encoding, errors="replace").strip())
        rows.append(row)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow([f["name"] for f in spec])
        w.writerows(rows)
    print(f"{len(rows)}줄 변환 -> {a.output}")
    for no, n in short:
        print(f"  주의: {no}번째 줄이 {n}바이트로 규칙({need}바이트)보다 짧습니다.")


if __name__ == "__main__":
    main()
