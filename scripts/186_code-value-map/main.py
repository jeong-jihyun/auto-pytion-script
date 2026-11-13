"""시스템 이관·연계 때 CSV 안의 코드값을 매핑표대로 새 코드로 바꾸는 스크립트.

생각의 흐름:
  1) ERP·차세대 이관을 하면 옛 시스템 코드(예: 거래구분 '01')를 새 시스템 코드('BUY')로 바꿔야 합니다.
     열이 여러 개고 코드도 많아서 엑셀 VLOOKUP 으로 하면 빠뜨리기 쉽습니다.
  2) 매핑표는 CSV 하나로 받습니다: 열이름,원본코드,대상코드
     → 한 파일에 여러 열의 매핑을 같이 적을 수 있습니다.
  3) 매핑에 없는 값이 나오면 어떻게 할지 고릅니다.
     - keep(기본): 원래 값을 그대로 두고 '매핑 없음' 목록에 적기
     - default:    --default 로 준 값으로 채우기
     - fail:       하나라도 있으면 결과를 저장하지 않고 멈추기(이관 리허설용)
  4) 매핑표 자체도 검사합니다: 같은 열·같은 원본코드가 서로 다른 대상코드로 두 번 적히면 오류.
  5) 앞뒤 공백, 대소문자 차이 때문에 매핑이 안 되는 일이 많아서 --ignore-case 옵션을 둡니다.
"""
import argparse
import csv
import os
import sys
from collections import Counter, defaultdict


def norm(v, ignore_case):
    v = (v or "").strip()
    return v.upper() if ignore_case else v


def load_map(path, ignore_case):
    mapping, errors = defaultdict(dict), []
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        need = {"열이름", "원본코드", "대상코드"}
        if not need.issubset(reader.fieldnames or []):
            sys.exit(f"[오류] 매핑표에는 {sorted(need)} 열이 있어야 합니다. 있는 열: {reader.fieldnames}")
        for i, r in enumerate(reader, start=2):
            col, src, dst = r["열이름"].strip(), norm(r["원본코드"], ignore_case), r["대상코드"].strip()
            old = mapping[col].get(src)
            if old is not None and old != dst:
                errors.append(f"매핑표 {i}행: [{col}] '{src}' 가 '{old}' 와 '{dst}' 두 가지로 적혀 있음")
            mapping[col][src] = dst
    return mapping, errors


def main():
    ap = argparse.ArgumentParser(description="매핑표대로 CSV 코드값 바꾸기")
    ap.add_argument("input", help="바꿀 데이터 CSV")
    ap.add_argument("mapfile", help="매핑표 CSV (열: 열이름,원본코드,대상코드)")
    ap.add_argument("--on-missing", choices=["keep", "default", "fail"], default="keep",
                    help="매핑 없는 값 처리 (기본 keep)")
    ap.add_argument("--default", default="", help="--on-missing default 일 때 넣을 값")
    ap.add_argument("--ignore-case", action="store_true", help="대소문자 구분 없이 맞추기")
    ap.add_argument("--keep-original", action="store_true", help="바뀐 열 옆에 '열이름_원본' 열을 남기기")
    ap.add_argument("--output", default="output/mapped.csv")
    ap.add_argument("--unmapped", default="output/unmapped.csv", help="매핑 없는 값 목록")
    args = ap.parse_args()

    mapping, map_errors = load_map(args.mapfile, args.ignore_case)
    if map_errors:
        for e in map_errors:
            print(f"[오류] {e}")
        sys.exit("매핑표를 먼저 고쳐 주세요.")

    with open(args.input, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fields = list(reader.fieldnames or [])
        rows = list(reader)
    target_cols = [c for c in mapping if c in fields]
    for c in mapping:
        if c not in fields:
            print(f"[주의] 매핑표의 열 '{c}' 이(가) 데이터에 없어 건너뜁니다.")
    if not target_cols:
        sys.exit("[오류] 바꿀 열이 하나도 없습니다.")

    out_fields = []
    for c in fields:
        out_fields.append(c)
        if args.keep_original and c in target_cols:
            out_fields.append(f"{c}_원본")

    missing = Counter()
    first_row = {}
    done = Counter()
    for i, r in enumerate(rows, start=2):
        for c in target_cols:
            raw = r[c]
            if args.keep_original:
                r[f"{c}_원본"] = raw
            key = norm(raw, args.ignore_case)
            if key == "":
                continue                         # 빈 칸은 그대로 둡니다
            if key in mapping[c]:
                r[c] = mapping[c][key]
                done[c] += 1
            else:
                missing[(c, raw.strip())] += 1
                first_row.setdefault((c, raw.strip()), i)
                if args.on_missing == "default":
                    r[c] = args.default

    print(f"읽은 행: {len(rows)}")
    for c in target_cols:
        print(f"  [{c}] 바꾼 칸 {done[c]}개, 매핑 표 {len(mapping[c])}개")
    if missing:
        print(f"매핑 없는 값 {len(missing)}종류:")
        for (c, v), n in missing.most_common():
            print(f"  - [{c}] '{v}' {n}건 (처음 {first_row[(c, v)]}행)")

    for p in (args.output, args.unmapped):
        d = os.path.dirname(p)
        if d:
            os.makedirs(d, exist_ok=True)
    with open(args.unmapped, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["열이름", "값", "건수", "처음나온행"])
        for (c, v), n in missing.most_common():
            w.writerow([c, v, n, first_row[(c, v)]])

    if missing and args.on_missing == "fail":
        sys.exit("[중단] 매핑 없는 값이 있어 결과를 저장하지 않았습니다(--on-missing fail). 매핑표를 보완하세요.")

    with open(args.output, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=out_fields)
        w.writeheader()
        w.writerows(rows)
    print(f"저장: {args.output} / 매핑 없는 값 목록: {args.unmapped}")


if __name__ == "__main__":
    main()
