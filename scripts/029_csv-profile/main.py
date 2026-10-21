"""CSV 열 요약(프로파일링) 스크립트.

CSV 를 받으면 열마다 아래를 정리해서 보여 줍니다.
  채워진 칸 수 / 빈 칸 수 / 서로 다른 값 수 / 숫자 열이면 최소·최대·합계·평균 /
  글자 열이면 가장 많이 나온 값 3개
데이터를 받자마자 '어떻게 생겼는지' 훑어볼 때 씁니다. 결과는 화면과 CSV 로 나옵니다.
"""
import argparse
import csv
from collections import Counter
from pathlib import Path


def to_number(text):
    """쉼표가 든 숫자('1,000')도 숫자로 읽습니다. 못 읽으면 None."""
    try:
        return float(text.replace(",", ""))
    except ValueError:
        return None


def fmt(x):
    """숫자를 읽기 쉽게: 정수면 소수점 없이, 아니면 소수 2자리까지."""
    return str(int(x)) if float(x).is_integer() else f"{x:.2f}"


def main():
    p = argparse.ArgumentParser(description="CSV 열 요약")
    p.add_argument("input", type=Path)
    p.add_argument("-o", "--output", type=Path, default=Path("output/profile.csv"))
    a = p.parse_args()

    with a.input.open(newline="", encoding="utf-8-sig") as fp:
        r = csv.DictReader(fp)
        header = r.fieldnames or []
        rows = list(r)
    out = [["열", "채움", "빈칸", "고유값", "종류", "최소", "최대", "합계", "평균", "많이 나온 값"]]
    for col in header:
        vals = [(row.get(col) or "").strip() for row in rows]
        filled = [v for v in vals if v]
        nums = [to_number(v) for v in filled]
        is_num = bool(filled) and all(n is not None for n in nums)
        if is_num:
            s = sum(nums)
            line = [col, len(filled), len(vals) - len(filled), len(set(filled)), "숫자",
                    fmt(min(nums)), fmt(max(nums)), fmt(s), f"{s / len(nums):.2f}", ""]
        else:
            top = "; ".join(f"{v}({n})" for v, n in Counter(filled).most_common(3))
            line = [col, len(filled), len(vals) - len(filled), len(set(filled)), "글자", "", "", "", "", top]
        out.append(line)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        csv.writer(fp).writerows(out)
    print(f"{len(rows)}행 x {len(header)}열 -> {a.output}")
    for line in out[1:]:
        print(f"  {line[0]}: 채움 {line[1]}, 빈칸 {line[2]}, 고유 {line[3]}, {line[4]}",
              f"(최소 {line[5]} ~ 최대 {line[6]}, 평균 {line[8]})" if line[4] == "숫자" else f"[{line[9]}]")


if __name__ == "__main__":
    main()
