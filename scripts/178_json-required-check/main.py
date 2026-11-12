"""여러 JSON 파일(API 응답, 연동 전문, 설정)이 약속한 모양(필수 키, 자료형, 허용값)을 지키는지 검사하는 스크립트.

생각의 흐름:
  1) 외부 기관·다른 팀과 JSON으로 주고받다 보면 '필수 키가 빠짐', '숫자여야 하는데 글자로 옴',
     '정해진 코드 말고 다른 값'이 섞여 장애가 납니다. 받은 파일을 미리 검사하면 원인을 빨리 찾습니다.
  2) 규칙 파일에 '경로 → 조건'을 적습니다. 경로는 점으로 내려가고, 목록 안은 [] 로 표시합니다.
       예) "header.trx_code": {"type": "string", "required": true, "enum": ["ORD", "CXL"]}
           "body.items[].qty":  {"type": "integer", "min": 1}
  3) 경로를 따라 값을 모두 찾고(목록이면 원소마다), 없으면 필수 위반, 있으면 자료형·허용값·범위·길이·정규식을 봅니다.
  4) 파이썬에서 True도 정수로 취급되는 함정이 있어, integer/number 검사에서 bool은 따로 뺍니다.
  5) 외부 패키지(jsonschema) 없이 자주 쓰는 검사만 담은 '가벼운' 검사기입니다.
"""
import argparse
import csv
import glob
import json
import os
import re

TYPES = {
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "array": lambda v: isinstance(v, list),
    "object": lambda v: isinstance(v, dict),
    "null": lambda v: v is None,
}


def find(data, path):
    """경로를 따라 (실제경로, 값) 목록을 돌려줍니다. 중간에 없으면 (경로, MISSING)."""
    results = [("", data)]
    for part in path.split("."):
        is_list = part.endswith("[]")
        key = part[:-2] if is_list else part
        nxt = []
        for where, cur in results:
            here = f"{where}.{key}" if where else key
            if cur is NOT_LIST:
                nxt.append((where, NOT_LIST))   # 목록이 아니었던 위치를 그대로 넘깁니다
                continue
            if cur is MISSING or not isinstance(cur, dict) or key not in cur:
                nxt.append((here, MISSING))
                continue
            val = cur[key]
            if is_list:
                if not isinstance(val, list):
                    nxt.append((here, NOT_LIST))
                else:
                    nxt.extend((f"{here}[{i}]", v) for i, v in enumerate(val))
            else:
                nxt.append((here, val))
        results = nxt
    return results


MISSING = object()
NOT_LIST = object()


def check_value(rule, val):
    errs = []
    types = rule.get("type")
    if types:
        types = types if isinstance(types, list) else [types]
        if not any(TYPES[t](val) for t in types):
            errs.append(f"자료형이 {'/'.join(types)} 이어야 하는데 {type(val).__name__} ({json.dumps(val, ensure_ascii=False)[:30]})")
            return errs
    if "enum" in rule and val not in rule["enum"]:
        errs.append(f"허용값 {rule['enum']} 이 아님: {val!r}")
    if isinstance(val, (int, float)) and not isinstance(val, bool):
        if "min" in rule and val < rule["min"]:
            errs.append(f"{rule['min']} 보다 작음: {val}")
        if "max" in rule and val > rule["max"]:
            errs.append(f"{rule['max']} 보다 큼: {val}")
    if isinstance(val, str):
        if "max_len" in rule and len(val) > rule["max_len"]:
            errs.append(f"길이 {len(val)} > {rule['max_len']}")
        if "pattern" in rule and not re.fullmatch(rule["pattern"], val):
            errs.append(f"형식({rule['pattern']})에 맞지 않음: {val!r}")
    return errs


def main():
    ap = argparse.ArgumentParser(description="JSON 파일 필수 키·자료형·허용값 검사")
    ap.add_argument("inputs", nargs="+", help="JSON 파일 또는 *.json 패턴")
    ap.add_argument("--rules", required=True, help="규칙 JSON")
    ap.add_argument("-o", "--out", default="out/json_check.csv")
    args = ap.parse_args()

    with open(args.rules, encoding="utf-8") as f:
        rules = json.load(f)
    files = sorted({p for pat in args.inputs for p in (glob.glob(pat) or [pat])})

    problems, ok_files = [], 0
    for path in files:
        try:
            with open(path, encoding="utf-8-sig") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            problems.append([path, "(파일)", f"JSON으로 읽을 수 없음: {e}"])
            continue
        before = len(problems)
        seen_not_list = set()
        for rpath, rule in rules.items():
            for where, val in find(data, rpath):
                if val is MISSING:
                    if rule.get("required"):
                        problems.append([path, where, "필수 키가 없음"])
                elif val is NOT_LIST:
                    if where not in seen_not_list:   # 같은 위치는 한 번만 알립니다
                        seen_not_list.add(where)
                        problems.append([path, where, "목록([])이어야 함"])
                else:
                    for e in check_value(rule, val):
                        problems.append([path, where, e])
        if len(problems) == before:
            ok_files += 1

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["파일", "위치", "문제"])
        w.writerows(problems)

    print(f"파일 {len(files)}개 검사: 통과 {ok_files}개, 문제 {len(problems)}건")
    for p in problems[:30]:
        print(f"  {os.path.basename(p[0])} | {p[1]} | {p[2]}")
    if len(problems) > 30:
        print(f"  ... 나머지 {len(problems) - 30}건은 파일을 보세요")
    print(f"결과 → {args.out}")


if __name__ == "__main__":
    main()
