"""영업일(근무일) 계산 스크립트.

시작일부터 N 영업일 뒤의 날짜를 구하거나, 두 날짜 사이 영업일 수를 셉니다.
주말은 자동 제외하고, 공휴일은 파일(--holidays, 한 줄에 YYYY-MM-DD)로 알려 줍니다.
(공휴일은 해마다 달라 코드에 고정하지 않았어요.)
"""
import argparse
from datetime import date, timedelta
from pathlib import Path


def 공휴일읽기(path):
    if not path:
        return set()
    return {date.fromisoformat(s.strip()) for s in path.read_text(encoding="utf-8").splitlines()
            if s.strip() and not s.startswith("#")}


def 영업일인가(d, hol):
    return d.weekday() < 5 and d not in hol


def main():
    p = argparse.ArgumentParser(description="영업일 계산")
    sub = p.add_subparsers(dest="cmd", required=True)
    a1 = sub.add_parser("add", help="N 영업일 뒤 날짜")
    a1.add_argument("start")
    a1.add_argument("days", type=int)
    a2 = sub.add_parser("count", help="두 날짜 사이 영업일 수 (시작 포함, 끝 포함)")
    a2.add_argument("start")
    a2.add_argument("end")
    for s in (a1, a2):
        s.add_argument("--holidays", type=Path)
    a = p.parse_args()
    hol = 공휴일읽기(a.holidays)
    s = date.fromisoformat(a.start)
    if a.cmd == "add":
        d, left, step = s, abs(a.days), 1 if a.days >= 0 else -1
        while left:
            d += timedelta(days=step)
            if 영업일인가(d, hol):
                left -= 1
        print(f"{s} 에서 {a.days} 영업일 후: {d} ({'월화수목금토일'[d.weekday()]})")
    else:
        e = date.fromisoformat(a.end)
        n = sum(영업일인가(s + timedelta(days=i), hol) for i in range((e - s).days + 1))
        print(f"{s} ~ {e} 영업일 수: {n}일")


if __name__ == "__main__":
    main()
