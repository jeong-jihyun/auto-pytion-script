"""거래(트랜잭션) 로그에서 초당 처리 건수(TPS)를 세어 피크 시각과 분 단위 추이를 보여 주는 스크립트.

생각의 흐름:
  1) 증권 주문·이체 같은 시스템은 '평균'보다 '가장 몰린 순간'이 중요합니다.
     장 시작 9시 직후처럼 순간 TPS가 용량을 넘으면 지연·장애가 납니다.
  2) 로그 한 줄마다 시각(초 단위)을 뽑아 같은 초끼리 개수를 셉니다. 그게 TPS입니다.
  3) 거래가 없던 초도 0건으로 넣어야 평균·백분위가 정확하므로, 처음~끝 초를 모두 채웁니다.
  4) 상위 N개 피크 초, 분 단위 평균·최대 TPS, p95·p99 TPS를 보여 주고,
     --limit(설계 용량)을 주면 넘은 초를 따로 표시합니다.
  5) 시각 형식은 '2026-11-12 09:00:01' 이나 '2026-11-12T09:00:01.123' 처럼 흔한 모양을 정규식으로 찾고,
     --grep 으로 특정 거래(예: ORDER)만 셀 수 있습니다.
"""
import argparse
import csv
import os
import re
from collections import Counter
from datetime import datetime, timedelta

TS_RE = re.compile(r"(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2}:\d{2})")


def percentile(sorted_vals, p):
    """정렬된 값에서 p 백분위(가장 가까운 순위 방식)."""
    if not sorted_vals:
        return 0
    k = max(0, min(len(sorted_vals) - 1, int(round(p / 100 * len(sorted_vals) + 0.5)) - 1))
    return sorted_vals[k]


def main():
    ap = argparse.ArgumentParser(description="거래 로그의 초당 처리 건수(TPS) 피크 분석")
    ap.add_argument("logs", nargs="+", help="로그 파일(여러 개 가능)")
    ap.add_argument("--grep", default="", help="이 글자가 들어간 줄만 셉니다(예: ORDER)")
    ap.add_argument("--top", type=int, default=5, help="피크 초 몇 개를 보여 줄지 (기본 5)")
    ap.add_argument("--limit", type=int, default=0, help="설계 용량 TPS. 넘은 초를 표시합니다")
    ap.add_argument("-o", "--out", default="out/tps_per_minute.csv", help="분 단위 결과 CSV")
    args = ap.parse_args()

    per_sec = Counter()
    skipped = 0
    for path in args.logs:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                if args.grep and args.grep not in line:
                    continue
                m = TS_RE.search(line)
                if not m:
                    skipped += 1
                    continue
                per_sec[datetime.strptime(m.group(1) + " " + m.group(2), "%Y-%m-%d %H:%M:%S")] += 1

    if not per_sec:
        print("시각이 있는 줄을 찾지 못했습니다. 로그 형식이나 --grep 을 확인하세요.")
        return

    # 거래가 없던 초도 0으로 채웁니다
    start, end = min(per_sec), max(per_sec)
    series = []
    t = start
    while t <= end:
        series.append((t, per_sec.get(t, 0)))
        t += timedelta(seconds=1)

    total = sum(c for _, c in series)
    vals = sorted(c for _, c in series)
    print(f"기간 {start} ~ {end} ({len(series)}초), 총 {total}건, 시각 없는 줄 {skipped}개 건너뜀")
    print(f"평균 TPS {total/len(series):.2f} / p95 {percentile(vals,95)} / p99 {percentile(vals,99)} / 최대 {vals[-1]}")

    print(f"\n[피크 상위 {args.top}초]")
    for t, c in sorted(series, key=lambda x: (-x[1], x[0]))[:args.top]:
        print(f"  {t}  {c}건")

    if args.limit:
        over = [(t, c) for t, c in series if c > args.limit]
        print(f"\n[용량 {args.limit} TPS 초과] {len(over)}초")
        for t, c in over[:20]:
            print(f"  {t}  {c}건 (+{c-args.limit})")

    # 분 단위 요약
    by_min = {}
    for t, c in series:
        key = t.replace(second=0)
        by_min.setdefault(key, []).append(c)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["분", "건수", "평균TPS", "최대TPS"])
        for k in sorted(by_min):
            cs = by_min[k]
            w.writerow([k.strftime("%Y-%m-%d %H:%M"), sum(cs), f"{sum(cs)/len(cs):.2f}", max(cs)])
    print(f"\n분 단위 요약 → {args.out}")


if __name__ == "__main__":
    main()
