"""서버·API 로그에서 주소(경로)별 응답시간 통계를 내는 스크립트.

로그 한 줄 예: 2026-10-24 09:00:01 GET /api/order 200 123ms
주소별로 건수, 평균, 중앙값(p50), p95, 최대, 5xx 오류 비율을 계산합니다.
형식이 다른 로그는 --pattern 으로 정규식을 바꿀 수 있습니다(그룹 이름: path, status, ms).
"""
import argparse
import csv
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

DEFAULT = r"^\S+ \S+ (?P<method>[A-Z]+) (?P<path>\S+) (?P<status>\d{3}) (?P<ms>\d+)ms"


def percentile(sorted_vals, pct):
    """가까운 순위(nearest-rank) 방식 백분위수."""
    if not sorted_vals:
        return 0
    k = max(1, math.ceil(pct / 100 * len(sorted_vals)))
    return sorted_vals[k - 1]


def main():
    p = argparse.ArgumentParser(description="로그 응답시간 통계")
    p.add_argument("input", type=Path, help="로그 파일")
    p.add_argument("--pattern", default=DEFAULT, help="정규식(path, status, ms 그룹 필요)")
    p.add_argument("--slow-ms", type=int, default=1000, help="이 값(ms) 이상이면 느린 요청으로 따로 세기")
    p.add_argument("-o", "--output", type=Path, default=Path("output/response_stats.csv"))
    a = p.parse_args()

    rx = re.compile(a.pattern)
    by_path = defaultdict(list)
    errors = defaultdict(int)
    bad_lines = 0
    with a.input.open(encoding="utf-8", errors="replace") as fp:
        for line in fp:
            if not line.strip():
                continue
            m = rx.search(line)
            if not m:
                bad_lines += 1
                continue
            path = m.group("path").split("?")[0]       # 물음표 뒤 값은 합쳐서 집계
            by_path[path].append(int(m.group("ms")))
            if m.group("status").startswith("5"):
                errors[path] += 1

    if not by_path:
        print("[오류] 읽을 수 있는 로그 줄이 없습니다. --pattern 을 확인하세요.")
        sys.exit(1)

    a.output.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for path, vals in by_path.items():
        s = sorted(vals)
        rows.append([path, len(s), round(sum(s) / len(s), 1), percentile(s, 50),
                     percentile(s, 95), s[-1], sum(1 for v in s if v >= a.slow_ms),
                     f"{errors[path] / len(s) * 100:.1f}%"])
    rows.sort(key=lambda x: -x[4])                      # p95 큰 순서
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["주소", "건수", "평균ms", "p50ms", "p95ms", "최대ms", f"느림(>={a.slow_ms}ms)", "5xx비율"])
        w.writerows(rows)
    print(f"[완료] 주소 {len(rows)}개, 요청 {sum(r[1] for r in rows)}건 -> {a.output}")
    print(f"  가장 느린(p95) 주소: {rows[0][0]} ({rows[0][4]}ms)")
    if bad_lines:
        print(f"[알림] 형식이 맞지 않아 건너뛴 줄 {bad_lines}개")


if __name__ == "__main__":
    main()
