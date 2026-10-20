"""CSV 데이터 검증 스크립트.

규칙 파일(JSON)에 따라 각 열을 검사하고, 틀린 곳을 '몇 번째 줄, 어느 열, 왜'로 알려 줍니다.
지원 규칙: required(필수), type(int/float/date), min, max, regex, allowed(허용값 목록)
"""
import argparse
import csv
import json
import re
from datetime import date
from pathlib import Path


def 검사(값, rule):
    v = 값.strip()
    if not v:
        return "비어 있음" if rule.get("required") else None
    t = rule.get("type")
    try:
        if t == "int":
            n = int(v)
        elif t == "float":
            n = float(v)
        elif t == "date":
            date.fromisoformat(v)
            n = None
        else:
            n = None
    except ValueError:
        return f"{t} 형식이 아님: {v}"
    if n is not None:
        if "min" in rule and n < rule["min"]:
            return f"{rule['min']}보다 작음: {v}"
        if "max" in rule and n > rule["max"]:
            return f"{rule['max']}보다 큼: {v}"
    if "regex" in rule and not re.fullmatch(rule["regex"], v):
        return f"형식 불일치: {v}"
    if "allowed" in rule and v not in rule["allowed"]:
        return f"허용값 아님: {v}"
    return None


def main():
    p = argparse.ArgumentParser(description="CSV 검증")
    p.add_argument("input", type=Path)
    p.add_argument("--rules", type=Path, required=True)
    a = p.parse_args()
    rules = json.loads(a.rules.read_text(encoding="utf-8"))
    errors, rows = [], 0
    with a.input.open(newline="", encoding="utf-8-sig") as fp:
        r = csv.DictReader(fp)
        for col in rules:
            if col not in r.fieldnames:
                raise SystemExit(f"오류: 규칙의 '{col}' 열이 CSV에 없습니다.")
        for i, row in enumerate(r, start=2):  # 1줄은 헤더
            rows += 1
            for col, rule in rules.items():
                msg = 검사(row.get(col) or "", rule)
                if msg:
                    errors.append(f"{i}번째 줄 [{col}] {msg}")
    print(f"검사 {rows}행, 문제 {len(errors)}건")
    for e in errors:
        print(" -", e)
    raise SystemExit(1 if errors else 0)


if __name__ == "__main__":
    main()
