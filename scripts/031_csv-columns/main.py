"""CSV 열 고르기·이름 바꾸기·순서 바꾸기 스크립트.

큰 CSV에서 필요한 열만 남기거나, 열 이름을 다른 시스템 양식에 맞게 바꿀 때 씁니다.
  --keep  남길 열을 원하는 순서대로 적습니다 (이 순서가 결과 열 순서가 됩니다)
  --rename '옛이름:새이름,옛이름2:새이름2'
  --drop  지울 열 (--keep 을 안 쓸 때만 의미가 있습니다)
"""
import argparse
import csv
import sys
from pathlib import Path


def split_list(text):
    """'a, b ,c' -> ['a','b','c'] (빈 항목은 버림)"""
    return [t.strip() for t in (text or "").split(",") if t.strip()]


def main():
    p = argparse.ArgumentParser(description="CSV 열 선택·이름 변경")
    p.add_argument("input", type=Path, help="입력 CSV")
    p.add_argument("-o", "--output", type=Path, default=Path("output/columns.csv"))
    p.add_argument("--keep", help="남길 열(쉼표로 구분, 이 순서대로 저장)")
    p.add_argument("--drop", help="지울 열(쉼표로 구분)")
    p.add_argument("--rename", help="이름 바꾸기 '옛:새,옛:새'")
    a = p.parse_args()

    with a.input.open(newline="", encoding="utf-8-sig") as fp:
        r = csv.DictReader(fp)
        header = r.fieldnames or []
        rows = list(r)

    # 1) 어떤 열을 어떤 순서로 쓸지 정합니다.
    cols = split_list(a.keep) or header[:]
    for d in split_list(a.drop):
        if d in cols:
            cols.remove(d)
    # 2) 없는 열 이름을 적었으면 바로 알려 줍니다(오타 방지).
    missing = [c for c in cols if c not in header]
    if missing:
        print(f"[오류] 입력 파일에 없는 열: {missing}\n  있는 열: {header}")
        sys.exit(1)
    # 3) 이름 바꾸기 규칙을 읽습니다.
    mapping = {}
    for item in split_list(a.rename):
        if ":" not in item:
            print(f"[오류] --rename 형식이 틀렸습니다: '{item}' ('옛:새' 로 적어 주세요)")
            sys.exit(1)
        old, new = item.split(":", 1)
        mapping[old.strip()] = new.strip()
    new_header = [mapping.get(c, c) for c in cols]

    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(new_header)
        for row in rows:
            w.writerow([row.get(c, "") for c in cols])
    print(f"{len(rows)}행, 열 {len(header)}개 -> {len(cols)}개: {new_header}")
    print(f"저장: {a.output}")


if __name__ == "__main__":
    main()
