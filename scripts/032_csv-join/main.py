"""CSV 결합(엑셀 VLOOKUP/조인 같은 일) 스크립트.

왼쪽 CSV(주 표)에 오른쪽 CSV(참고 표)의 열을 '키 열'이 같은 줄끼리 붙입니다.
  예) 주문 목록 + 고객 정보표 -> 주문마다 고객 등급·담당자를 붙이기
  --how left  : 왼쪽 줄은 모두 남김(오른쪽에 없으면 빈칸)  [기본]
  --how inner : 양쪽에 다 있는 줄만 남김
오른쪽 표에 같은 키가 여러 번 있으면 '첫 줄'을 쓰고 경고를 보여 줍니다.
"""
import argparse
import csv
from pathlib import Path


def read_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as fp:
        r = csv.DictReader(fp)
        return r.fieldnames or [], list(r)


def main():
    p = argparse.ArgumentParser(description="CSV 두 개를 키로 결합")
    p.add_argument("left", type=Path, help="왼쪽(주) CSV")
    p.add_argument("right", type=Path, help="오른쪽(참고) CSV")
    p.add_argument("--key", required=True, help="왼쪽의 키 열 이름")
    p.add_argument("--right-key", help="오른쪽의 키 열 이름(다르면 지정, 기본은 --key 와 같음)")
    p.add_argument("--how", choices=["left", "inner"], default="left")
    p.add_argument("-o", "--output", type=Path, default=Path("output/joined.csv"))
    a = p.parse_args()

    rkey = a.right_key or a.key
    lh, lrows = read_csv(a.left)
    rh, rrows = read_csv(a.right)
    for name, h, k in (("왼쪽", lh, a.key), ("오른쪽", rh, rkey)):
        if k not in h:
            raise SystemExit(f"[오류] {name} 파일에 '{k}' 열이 없습니다. 있는 열: {h}")

    # 오른쪽 표를 '키 -> 줄' 사전으로 만들어 두면 빨리 찾을 수 있습니다.
    lookup, dup = {}, set()
    for row in rrows:
        k = (row[rkey] or "").strip()
        if k in lookup:
            dup.add(k)
            continue
        lookup[k] = row
    if dup:
        print(f"[경고] 오른쪽 표에 키가 중복된 값 {sorted(dup)} -> 첫 줄만 사용했습니다.")

    # 오른쪽에서 붙일 열(키 제외). 이름이 겹치면 '_오른쪽'을 붙입니다.
    extra = [c for c in rh if c != rkey]
    extra_names = [c + "_오른쪽" if c in lh else c for c in extra]

    out, matched = [], 0
    for row in lrows:
        hit = lookup.get((row[a.key] or "").strip())
        if hit:
            matched += 1
        elif a.how == "inner":
            continue
        out.append(list(row.get(c, "") for c in lh) + [(hit or {}).get(c, "") for c in extra])

    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(lh + extra_names)
        w.writerows(out)
    print(f"왼쪽 {len(lrows)}행 중 {matched}행 매칭, 결과 {len(out)}행 -> {a.output}")
    if matched < len(lrows):
        print(f"  (짝을 못 찾은 줄 {len(lrows) - matched}개)")


if __name__ == "__main__":
    main()
