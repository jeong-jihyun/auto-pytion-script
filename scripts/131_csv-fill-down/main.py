"""엑셀 '병합된 셀'을 CSV로 내려받으면 생기는 빈칸을 바로 위 값으로 채우는 스크립트.

생각의 흐름:
  1) 엑셀 보고서는 보기 좋게 '부서' 칸을 여러 줄 병합해 둡니다.
     이걸 CSV로 저장하면 첫 줄에만 값이 있고 아래 줄은 비어 버려서, 집계·필터가 틀어집니다.
  2) 그래서 지정한 열(--cols)에서 빈칸을 만나면 '바로 위 줄의 값'으로 채웁니다(fill down).
  3) 상위 열이 바뀌면 하위 열은 이어 채우면 안 됩니다.
     예) 부서가 '영업'→'개발'로 바뀌었는데 팀 칸이 비었다면, 영업팀 이름을 끌어오면 틀립니다.
     --cols 에 적은 순서를 상위→하위로 보고, 상위 열 값이 새로 나오면 하위 열의 '기억'을 지웁니다.
  4) 원본은 건드리지 않고 새 파일로 저장하며, 채운 칸 수를 열별로 알려 줍니다.
  5) 모든 열이 빈 줄(완전 빈 줄)은 채우지 않고 그대로 둡니다(--drop-empty 를 주면 뺍니다).
"""
import argparse
import csv
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description="CSV 빈칸을 위 값으로 채우기(병합셀 풀기)")
    p.add_argument("input", type=Path, help="입력 CSV")
    p.add_argument("--cols", required=True, help="채울 열 이름, 쉼표로(상위→하위 순서). 예: 부서,팀")
    p.add_argument("--drop-empty", action="store_true", help="완전히 빈 줄은 빼고 저장")
    p.add_argument("-o", "--output", type=Path, default=Path("output/filled.csv"))
    a = p.parse_args()

    cols = [c.strip() for c in a.cols.split(",") if c.strip()]
    with a.input.open(newline="", encoding="utf-8-sig") as fp:
        reader = csv.DictReader(fp)
        header = reader.fieldnames or []
        rows = list(reader)
    missing = [c for c in cols if c not in header]
    if missing:
        raise SystemExit(f"[오류] CSV에 없는 열: {', '.join(missing)} (있는 열: {', '.join(header)})")

    last = {c: "" for c in cols}       # 열별로 마지막으로 본 값
    filled = {c: 0 for c in cols}      # 열별로 채운 칸 수
    out, dropped = [], 0
    for r in rows:
        if not any((v or "").strip() for v in r.values()):
            if a.drop_empty:
                dropped += 1
            else:
                out.append(r)
            continue
        for i, c in enumerate(cols):
            v = (r.get(c) or "").strip()
            if v:
                if v != last[c]:
                    # 상위 열 값이 새로 나왔으니 하위 열 기억은 지웁니다
                    for lower in cols[i + 1:]:
                        last[lower] = ""
                last[c] = v
            elif last[c]:
                r[c] = last[c]
                filled[c] += 1
        out.append(r)

    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.DictWriter(fp, fieldnames=header)
        w.writeheader()
        w.writerows(out)
    print(f"전체 {len(rows)}줄 → 저장 {len(out)}줄 (빈 줄 제외 {dropped}줄)")
    for c in cols:
        print(f"  {c}: {filled[c]}칸 채움")
    print(f"저장: {a.output}")


if __name__ == "__main__":
    main()
