"""매일 받는 연동 CSV 파일들의 '열 구성(헤더)'이 약속한 형식과 달라졌는지 점검하는 스크립트.

생각의 흐름:
  1) 기준 형식 파일(JSON)에 파일 이름 패턴별로 '있어야 할 열 이름과 순서'를 적어 둡니다.
  2) 폴더 안 CSV마다 첫 줄(헤더)만 읽습니다. 큰 파일도 금방 끝납니다.
  3) 기준과 비교해 다음을 알려 줍니다.
     - 빠진 열 / 새로 생긴 열 / 순서가 바뀐 열 / 이름 앞뒤 공백·대소문자만 다른 열
     - 중복된 열 이름, 구분자가 쉼표가 아닌 것 같은 경우(헤더가 열 1개로 읽힘)
  4) 문제가 있으면 종료 코드 1로 끝나서, 배치 스케줄러가 '다음 단계 멈춤'으로 쓸 수 있습니다.
"""
import argparse
import csv
import fnmatch
import json
import sys
from pathlib import Path


def read_header(path, encoding):
    with path.open(newline="", encoding=encoding, errors="replace") as fp:
        first = fp.readline()
    if not first.strip():
        return [], ""
    delim = ","
    try:
        delim = csv.Sniffer().sniff(first, delimiters=",;\t|").delimiter
    except csv.Error:
        pass
    return next(csv.reader([first], delimiter=delim)), delim


def compare(expected, actual, strict_order):
    problems = []
    norm = lambda s: s.strip().lower()
    exp_n = [norm(x) for x in expected]
    act_n = [norm(x) for x in actual]
    for x in expected:
        if norm(x) not in act_n:
            problems.append(f"빠진 열: {x}")
    for x in actual:
        if norm(x) not in exp_n:
            problems.append(f"새로 생긴 열: {x}")
    for e in expected:
        for a_ in actual:
            if norm(e) == norm(a_) and e != a_:
                problems.append(f"표기 차이: '{a_}' (기준 '{e}')")
    dups = {x for x in act_n if act_n.count(x) > 1}
    for d in sorted(dups):
        problems.append(f"중복된 열: {d}")
    common_exp = [x for x in exp_n if x in act_n]
    common_act = [x for x in act_n if x in exp_n and x not in dups]
    if strict_order and common_exp != common_act and not dups:
        problems.append("열 순서 바뀜: " + " → ".join(common_act))
    return problems


def main():
    p = argparse.ArgumentParser(description="연동 CSV 헤더(열 구성) 변경 점검")
    p.add_argument("folder", type=Path, help="점검할 CSV 폴더")
    p.add_argument("--schema", type=Path, default=Path(__file__).with_name("sample") / "schema.json")
    p.add_argument("--encoding", default="utf-8-sig")
    p.add_argument("--ignore-order", action="store_true", help="열 순서는 검사하지 않기")
    p.add_argument("-o", "--output", type=Path, default=Path("output/header_check.csv"))
    a = p.parse_args()

    schema = json.loads(a.schema.read_text(encoding="utf-8"))
    results, bad = [], 0
    for f in sorted(a.folder.glob("*.csv")):
        rule = next(((pat, cols) for pat, cols in schema.items()
                     if not pat.startswith("_") and fnmatch.fnmatch(f.name, pat)), None)
        if rule is None:
            results.append([f.name, "", "기준 없음", "schema.json 에 맞는 패턴이 없습니다"])
            continue
        header, delim = read_header(f, a.encoding)
        if not header:
            probs = ["빈 파일(헤더 없음)"]
        else:
            probs = compare(rule[1], header, not a.ignore_order)
            if delim != ",":
                probs.insert(0, f"구분자가 쉼표가 아님('{delim}')")
        if probs:
            bad += 1
        results.append([f.name, rule[0], "이상" if probs else "정상", " / ".join(probs)])

    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["파일", "적용 패턴", "결과", "내용"])
        w.writerows(results)
    print(f"파일 {len(results)}개 점검, 이상 {bad}개 → {a.output}")
    for name, _, res, msg in results:
        if res != "정상":
            print(f"  - {name}: {res} {msg}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
