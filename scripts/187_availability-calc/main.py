"""장애 이력 CSV로 서비스별 한 달 가용률(%)을 계산하고, SLA 목표와 비교하는 스크립트.

생각의 흐름:
  1) 월간 운영 보고에는 "이번 달 가용률 99.95%" 같은 숫자가 꼭 들어갑니다.
     가용률 = (전체 시간 - 장애 시간) / 전체 시간 × 100
  2) 장애 기록은 그냥 더하면 틀립니다.
     - 같은 시간대에 장애가 두 건 겹치면 두 번 세게 됩니다 → 겹치는 구간을 먼저 합칩니다.
     - 월말 23시에 시작해 다음 달 1시에 끝난 장애는 이번 달 몫만 셉니다 → 달 경계로 자릅니다.
  3) 계획된 점검(사전 공지)은 SLA 계산에서 빼는 회사가 많습니다. 기본은 빼고, --include-planned 로 넣을 수 있습니다.
  4) 목표(예: 99.9%)가 있으면 '한 달에 허용되는 장애 시간'과 '아직 남은 여유'를 같이 보여 줍니다.
"""
import argparse
import calendar
import csv
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta

FMT_LIST = ["%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M"]


def parse_dt(s):
    s = s.strip()
    for fmt in FMT_LIST:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    raise ValueError(f"날짜시간 형식을 알 수 없음: '{s}' (예: 2026-10-05 14:30)")


def merge(intervals):
    """겹치거나 맞닿은 구간을 하나로 합칩니다."""
    out = []
    for s, e in sorted(intervals):
        if out and s <= out[-1][1]:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return out


def mins(td):
    return td.total_seconds() / 60


def main():
    ap = argparse.ArgumentParser(description="장애 이력으로 월 가용률 계산")
    ap.add_argument("input", help="장애 CSV (서비스,시작,종료,계획점검[Y/N],내용)")
    ap.add_argument("--month", required=True, help="계산할 달 (YYYY-MM)")
    ap.add_argument("--target", type=float, default=99.9, help="가용률 목표 %% (기본 99.9)")
    ap.add_argument("--include-planned", action="store_true", help="계획 점검도 장애 시간에 넣기")
    ap.add_argument("--services", help="장애가 없던 서비스도 표에 넣으려면 쉼표로 이름 나열")
    ap.add_argument("--output", default="output/availability.csv")
    args = ap.parse_args()

    try:
        y, m = map(int, args.month.split("-"))
        m_start = datetime(y, m, 1)
        m_end = m_start + timedelta(days=calendar.monthrange(y, m)[1])
    except ValueError:
        sys.exit("[오류] --month 는 2026-10 처럼 적어 주세요.")
    total_min = mins(m_end - m_start)

    per_service, planned_min, problems = defaultdict(list), defaultdict(float), []
    with open(args.input, encoding="utf-8-sig", newline="") as f:
        for i, r in enumerate(csv.DictReader(f), start=2):
            try:
                s, e = parse_dt(r["시작"]), parse_dt(r["종료"])
            except (ValueError, KeyError) as ex:
                problems.append(f"{i}행: {ex}")
                continue
            if e <= s:
                problems.append(f"{i}행: 종료가 시작보다 빠르거나 같음")
                continue
            s, e = max(s, m_start), min(e, m_end)          # 이번 달 몫만
            if e <= s:
                continue
            svc = r["서비스"].strip()
            planned = r.get("계획점검", "").strip().upper() in ("Y", "예", "YES")
            if planned and not args.include_planned:
                planned_min[svc] += mins(e - s)
                continue
            per_service[svc].append((s, e))

    names = set(per_service) | set(planned_min)
    if args.services:
        names |= {x.strip() for x in args.services.split(",") if x.strip()}
    allowed = total_min * (100 - args.target) / 100

    result = []
    for svc in sorted(names):
        merged = merge(per_service.get(svc, []))
        down = sum(mins(e - s) for s, e in merged)
        avail = (total_min - down) / total_min * 100
        result.append({
            "서비스": svc, "장애건수(합친후)": len(merged), "장애분": round(down, 1),
            "계획점검분(제외)": round(planned_min.get(svc, 0), 1),
            "가용률%": f"{avail:.3f}", "목표%": args.target,
            "허용분": round(allowed, 1), "남은여유분": round(allowed - down, 1),
            "판정": "달성" if avail >= args.target else "미달",
        })

    d = os.path.dirname(args.output)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(args.output, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(result[0].keys()) if result else ["서비스"])
        w.writeheader()
        w.writerows(result)

    print(f"{args.month} 전체 {total_min:,.0f}분, 목표 {args.target}% → 허용 장애 {allowed:.1f}분")
    for r in result:
        print(f"  {r['서비스']:<10} 가용률 {r['가용률%']}%  장애 {r['장애분']}분"
              f" (계획점검 제외 {r['계획점검분(제외)']}분)  여유 {r['남은여유분']}분  → {r['판정']}")
    for p in problems:
        print(f"[건너뜀] {p}")
    print(f"저장: {args.output}")


if __name__ == "__main__":
    main()
