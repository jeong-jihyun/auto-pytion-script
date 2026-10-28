"""JSON 한 줄씩 쌓이는 구조화 로그(JSON Lines)를 조건으로 거르고, 원하는 필드별로 집계하는 스크립트.

생각의 흐름:
  1) 요즘 서버·배치 로그는 {"ts": ..., "level": "ERROR", "service": "order", ...} 처럼 한 줄에 JSON 하나로 남깁니다.
     텍스트 로그용 도구(004 로그 분석)로는 필드를 제대로 나눠 보기 어렵습니다.
  2) 그래서 줄마다 json.loads 로 읽고
       - --where level=ERROR, --where service=order 처럼 조건(여러 개면 모두 만족)으로 거르고
       - --by service,code 처럼 필드 조합별로 건수를 세고
       - --value latency_ms 를 주면 그 숫자 필드의 평균·최대·p95 를 같이 냅니다.
  3) 필드가 안쪽에 있으면(예: {"http": {"status": 500}}) 점으로 이어 http.status 처럼 씁니다.
  4) JSON이 깨진 줄은 멈추지 않고 세어서 몇 번째 줄인지 앞쪽 몇 개만 알려 줍니다.
  5) .gz 로 압축된 로그도 바로 읽습니다(121 로그 압축 스크립트와 함께 쓰기 좋게).
  6) --where 는 =(같음), !=(다름), >=, <= (숫자 비교), ~(포함) 을 지원합니다.
"""
import argparse
import csv
import gzip
import json
import re
from collections import defaultdict
from pathlib import Path

OPS = [">=", "<=", "!=", "=", "~"]


def get(obj, path):
    for part in path.split("."):
        if isinstance(obj, dict) and part in obj:
            obj = obj[part]
        else:
            return None
    return obj


def parse_where(text):
    for op in OPS:
        if op in text:
            k, v = text.split(op, 1)
            return k.strip(), op, v.strip()
    raise SystemExit(f"[오류] 조건 형식이 틀렸습니다: {text} (예: level=ERROR, latency_ms>=1000)")


def match(rec, cond):
    k, op, v = cond
    x = get(rec, k)
    if x is None:
        return op == "!="
    if op in (">=", "<="):
        try:
            return float(x) >= float(v) if op == ">=" else float(x) <= float(v)
        except (TypeError, ValueError):
            return False
    s = str(x)
    return {"=": s == v, "!=": s != v, "~": v in s}[op]


def open_any(path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8")
    return path.open(encoding="utf-8")


def pct(values, q):
    v = sorted(values)
    idx = max(0, min(len(v) - 1, round(q * (len(v) - 1))))
    return v[idx]


def main():
    p = argparse.ArgumentParser(description="JSON Lines 로그 필터·집계")
    p.add_argument("files", nargs="+", type=Path, help="로그 파일(.jsonl, .log, .gz)")
    p.add_argument("--where", action="append", default=[], help="조건, 여러 번 가능. 예: level=ERROR")
    p.add_argument("--by", default="level", help="집계 기준 필드, 쉼표로(기본 level)")
    p.add_argument("--value", default="", help="숫자 통계를 낼 필드(예: latency_ms)")
    p.add_argument("--top", type=int, default=20, help="화면에 보여 줄 상위 개수")
    p.add_argument("--export", type=Path, help="조건에 맞는 원본 줄을 이 파일로 저장(.jsonl)")
    p.add_argument("-o", "--output", type=Path, default=Path("output/jsonl_summary.csv"))
    a = p.parse_args()

    conds = [parse_where(w) for w in a.where]
    keys = [k.strip() for k in a.by.split(",") if k.strip()]
    groups = defaultdict(lambda: {"n": 0, "vals": []})
    total = hit = 0
    bad = []
    exp = None
    if a.export:
        a.export.parent.mkdir(parents=True, exist_ok=True)
        exp = a.export.open("w", encoding="utf-8")
    for f in a.files:
        with open_any(f) as fp:
            for no, line in enumerate(fp, start=1):
                line = line.strip()
                if not line:
                    continue
                total += 1
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    bad.append(f"{f.name}:{no}")
                    continue
                if not isinstance(rec, dict) or not all(match(rec, c) for c in conds):
                    continue
                hit += 1
                if exp:
                    exp.write(line + "\n")
                g = groups[tuple(str(get(rec, k)) if get(rec, k) is not None else "(없음)" for k in keys)]
                g["n"] += 1
                if a.value:
                    v = get(rec, a.value)
                    if isinstance(v, (int, float)) and not isinstance(v, bool):
                        g["vals"].append(v)
                    elif isinstance(v, str) and re.fullmatch(r"-?\d+(\.\d+)?", v):
                        g["vals"].append(float(v))
    if exp:
        exp.close()

    ordered = sorted(groups.items(), key=lambda kv: kv[1]["n"], reverse=True)
    header = keys + ["건수", "비율(%)"]
    if a.value:
        header += [f"{a.value}_평균", f"{a.value}_p95", f"{a.value}_최대"]
    out = []
    for k, g in ordered:
        row = list(k) + [g["n"], round(g["n"] / hit * 100, 1) if hit else 0]
        if a.value:
            vs = g["vals"]
            row += [round(sum(vs) / len(vs), 1), pct(vs, 0.95), max(vs)] if vs else ["", "", ""]
        out.append(row)

    print(f"읽은 줄 {total}개, 조건 맞음 {hit}개, JSON 깨짐 {len(bad)}개" + (f" (예: {', '.join(bad[:5])})" if bad else ""))
    if conds:
        print("조건: " + " 그리고 ".join(f"{k}{op}{v}" for k, op, v in conds))
    print(" | ".join(header))
    for row in out[:a.top]:
        print(" | ".join(str(x) for x in row))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(header)
        w.writerows(out)
    print(f"저장: {a.output}" + (f", 걸러낸 원본: {a.export}" if a.export else ""))


if __name__ == "__main__":
    main()
