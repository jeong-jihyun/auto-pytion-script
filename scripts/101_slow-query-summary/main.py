"""DB 느린 쿼리(슬로우 쿼리) 로그를 '같은 모양의 SQL'끼리 묶어 횟수·평균·최대 시간을 정리하는 스크립트.

생각의 흐름:
  1) 로그에서 '실행시간'과 'SQL'을 뽑습니다. 줄 형식은 정규식(--pattern)으로 바꿀 수 있습니다.
     기본 형식: 2026-10-25 09:00:01 [1520ms] SELECT ...
  2) 같은 쿼리라도 WHERE id = 1, id = 2 처럼 값만 다르면 사실상 같은 쿼리입니다.
     숫자·문자열 값·IN (...) 목록을 ? 로 바꿔 '쿼리 모양(지문)'을 만들고, 지문별로 묶습니다.
  3) 지문별 건수, 총 시간, 평균, 최대, p95 를 계산해 '총 시간' 큰 순서로 정렬합니다.
     → 한 번 느린 쿼리보다 '자주 + 느린' 쿼리를 먼저 고치는 것이 효과가 큽니다.
"""
import argparse
import csv
import math
import re
from collections import defaultdict
from pathlib import Path

DEFAULT = r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+\[(?P<ms>[\d.]+)ms\]\s+(?P<sql>.+)$"


def fingerprint(sql):
    s = sql.strip().rstrip(";")
    s = re.sub(r"'(?:[^'\\]|\\.|'')*'", "?", s)        # 문자열 값
    s = re.sub(r"\b\d+(?:\.\d+)?\b", "?", s)              # 숫자 값
    s = re.sub(r"\(\s*\?(?:\s*,\s*\?)*\s*\)", "(?+)", s)  # IN (?, ?, ?) → (?+)
    s = re.sub(r"\s+", " ", s)
    return s.lower()


def p95(vals):
    v = sorted(vals)
    return v[max(0, math.ceil(len(v) * 0.95) - 1)]


def main():
    p = argparse.ArgumentParser(description="슬로우 쿼리 로그 요약")
    p.add_argument("log", type=Path)
    p.add_argument("--pattern", default=DEFAULT, help="ts, ms, sql 이름 그룹이 있는 정규식")
    p.add_argument("--min-ms", type=float, default=0, help="이보다 빠른 쿼리는 무시")
    p.add_argument("--top", type=int, default=10)
    p.add_argument("-o", "--output", type=Path, default=Path("output/slow_query_summary.csv"))
    a = p.parse_args()

    rx = re.compile(a.pattern)
    groups = defaultdict(lambda: {"times": [], "example": "", "first": "", "last": ""})
    skipped = 0
    with a.log.open(encoding="utf-8", errors="replace") as fp:
        for line in fp:
            m = rx.match(line.rstrip("\n"))
            if not m:
                skipped += 1
                continue
            ms = float(m.group("ms"))
            if ms < a.min_ms:
                continue
            g = groups[fingerprint(m.group("sql"))]
            g["times"].append(ms)
            g["example"] = g["example"] or m.group("sql").strip()
            g["first"] = g["first"] or m.group("ts")
            g["last"] = m.group("ts")

    rows = []
    for fp_, g in groups.items():
        t = g["times"]
        rows.append([fp_, len(t), round(sum(t)), round(sum(t) / len(t), 1), max(t), p95(t),
                     g["first"], g["last"], g["example"][:300]])
    rows.sort(key=lambda r: -r[2])
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["쿼리모양", "건수", "총시간ms", "평균ms", "최대ms", "p95ms", "처음", "마지막", "예시SQL"])
        w.writerows(rows)
    total = sum(r[1] for r in rows)
    print(f"쿼리 {total}건 → 모양 {len(rows)}개 (형식 안 맞는 줄 {skipped}개) → {a.output}")
    for i, r in enumerate(rows[:a.top], 1):
        print(f"  {i}. 총 {r[2]:,}ms / {r[1]}건 / 평균 {r[3]}ms : {r[0][:80]}")


if __name__ == "__main__":
    main()
