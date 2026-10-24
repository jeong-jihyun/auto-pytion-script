"""숫자 열에서 '튀는 값(이상치)'을 찾는 스크립트.

두 가지 방법을 고를 수 있습니다.
- iqr   : 사분위 범위 방법. 1사분위-1.5*IQR 보다 작거나 3사분위+1.5*IQR 보다 크면 이상치.
- zscore: 평균에서 표준편차의 N배(기본 3배) 넘게 떨어지면 이상치.
이상치는 '틀린 값'이 아니라 '확인할 값'입니다. 사람이 원인을 봐야 합니다.
"""
import argparse
import csv
import statistics
import sys
from pathlib import Path


def to_num(text):
    try:
        return float(str(text).replace(",", "").strip())
    except ValueError:
        return None


def quartiles(values):
    """1사분위·3사분위 (statistics.quantiles, 포함 방식)."""
    q = statistics.quantiles(values, n=4, method="inclusive")
    return q[0], q[2]


def main():
    p = argparse.ArgumentParser(description="이상치(튀는 값) 찾기")
    p.add_argument("input", type=Path)
    p.add_argument("--column", required=True, help="검사할 숫자 열 이름")
    p.add_argument("--method", choices=["iqr", "zscore"], default="iqr")
    p.add_argument("--k", type=float, help="iqr 기본 1.5, zscore 기본 3.0")
    p.add_argument("-o", "--output", type=Path, default=Path("output/outliers.csv"))
    a = p.parse_args()

    with a.input.open(newline="", encoding="utf-8-sig") as fp:
        r = csv.DictReader(fp)
        if a.column not in (r.fieldnames or []):
            print(f"[오류] 없는 열: {a.column} (있는 열: {r.fieldnames})")
            sys.exit(1)
        fields = list(r.fieldnames)
        rows = list(r)

    nums = [(i, to_num(row[a.column])) for i, row in enumerate(rows)]
    good = [v for _, v in nums if v is not None]
    if len(good) < 4:
        print("[오류] 숫자가 4개 이상 있어야 합니다.")
        sys.exit(1)

    if a.method == "iqr":
        k = a.k if a.k is not None else 1.5
        q1, q3 = quartiles(good)
        low, high = q1 - k * (q3 - q1), q3 + k * (q3 - q1)
        print(f"[기준] IQR 방식 k={k}: {low:,.1f} ~ {high:,.1f} 밖이면 이상치")
    else:
        k = a.k if a.k is not None else 3.0
        mean, sd = statistics.mean(good), statistics.pstdev(good)
        low, high = mean - k * sd, mean + k * sd
        print(f"[기준] z-score 방식 k={k}: 평균 {mean:,.1f}, 표준편차 {sd:,.1f} -> {low:,.1f} ~ {high:,.1f}")

    found = []
    for i, v in nums:
        if v is None:
            found.append((i, "숫자 아님"))
        elif v < low:
            found.append((i, "너무 작음"))
        elif v > high:
            found.append((i, "너무 큼"))

    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["줄번호"] + fields + ["사유"])
        for i, why in found:
            w.writerow([i + 2] + [rows[i][f] for f in fields] + [why])   # 줄번호: 머리글이 1번줄
    print(f"[완료] 전체 {len(rows)}행 중 확인할 행 {len(found)}개 -> {a.output}")
    for i, why in found:
        print(f"  - {i + 2}번 줄: {rows[i][a.column]} ({why})")


if __name__ == "__main__":
    main()
