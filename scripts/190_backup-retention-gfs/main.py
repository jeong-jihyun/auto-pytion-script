"""백업 파일을 '일 7개·주 4개·월 12개'처럼 GFS(할아버지-아버지-아들) 규칙으로 남기고, 나머지를 정리 후보로 고르는 스크립트.

생각의 흐름:
  1) 매일 백업을 받다 보면 디스크가 금방 찹니다. 그렇다고 '최근 N개만 남기기'를 하면 한 달 전 자료가 하나도 없습니다.
  2) GFS 규칙은 이렇게 남깁니다.
     - 일(아들):     최근 백업 날짜 7일치 (하루에 여러 개면 그날 가장 마지막 것)
     - 주(아버지):   최근 4주 각각에서 그 주의 가장 마지막 백업
     - 월(할아버지): 최근 12개월 각각에서 그 달의 가장 마지막 백업
     한 파일이 여러 규칙에 걸리면 한 번만 남기고, 왜 남겼는지(일/주/월)를 모두 적습니다.
  3) 날짜는 파일 이름에서 읽습니다(예: db_20261113.zip, db_2026-11-13_0200.zip). 수정 시각은 복사하면 바뀌므로 믿지 않습니다.
     이름에서 날짜를 못 읽은 파일은 건드리지 않고 따로 알려 줍니다.
  4) 기본은 미리보기(목록만 출력)입니다. --apply 를 주면 지우지 않고 --trash 폴더로 '옮기기'만 합니다.
     실제 삭제는 사람이 휴지통 폴더를 확인하고 직접 합니다.
  5) 폴더가 없어도 연습할 수 있게, 파일 이름 목록(txt)으로 시뮬레이션하는 --list-file 모드를 둡니다.
"""
import argparse
import os
import re
import shutil
import sys
from datetime import date

DATE_RE = re.compile(r"(20\d{2})-?(\d{2})-?(\d{2})")


def parse_date(name):
    m = DATE_RE.search(name)
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def pick_latest(files_by_key, limit):
    """키(날짜/주/월)별로 가장 마지막 파일 1개씩, 최근 키부터 limit 개."""
    keys = sorted(files_by_key, reverse=True)[:limit]
    return {k: max(files_by_key[k]) for k in keys}


def plan(names, days, weeks, months):
    dated, unknown = [], []
    for n in names:
        d = parse_date(n)
        (dated if d else unknown).append((d, n) if d else n)
    by_day, by_week, by_month = {}, {}, {}
    for d, n in dated:
        item = (d, n)                                       # (날짜, 이름) 순서라 max 가 '가장 마지막'
        by_day.setdefault(d, []).append(item)
        by_week.setdefault(tuple(d.isocalendar()[:2]), []).append(item)
        by_month.setdefault((d.year, d.month), []).append(item)

    reasons = {}
    for label, groups, limit in (("일", by_day, days), ("주", by_week, weeks), ("월", by_month, months)):
        for _, (d, n) in pick_latest(groups, limit).items():
            reasons.setdefault(n, []).append(label)
    keep = sorted(((d, n) for d, n in dated if n in reasons), reverse=True)
    drop = sorted(((d, n) for d, n in dated if n not in reasons), reverse=True)
    return keep, drop, reasons, unknown


def main():
    ap = argparse.ArgumentParser(description="GFS 규칙으로 백업 보관 정리")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--folder", help="백업 파일이 있는 폴더")
    src.add_argument("--list-file", help="파일 이름 목록 txt (연습·시뮬레이션용, 아무것도 옮기지 않음)")
    ap.add_argument("--pattern", default="", help="이름에 이 글자가 든 파일만 대상 (예: .zip)")
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--weeks", type=int, default=4)
    ap.add_argument("--months", type=int, default=12)
    ap.add_argument("--trash", default="retention_trash", help="--apply 때 옮길 폴더 (폴더 안 상대경로 또는 절대경로)")
    ap.add_argument("--apply", action="store_true", help="정리 후보를 휴지통 폴더로 실제로 옮기기(삭제는 안 함)")
    args = ap.parse_args()

    if args.list_file:
        with open(args.list_file, encoding="utf-8-sig") as f:
            names = [x.strip() for x in f if x.strip() and not x.startswith("#")]
    else:
        if not os.path.isdir(args.folder):
            sys.exit(f"[오류] 폴더가 없습니다: {args.folder}")
        names = sorted(n for n in os.listdir(args.folder) if os.path.isfile(os.path.join(args.folder, n)))
    names = [n for n in names if args.pattern in n]

    keep, drop, reasons, unknown = plan(names, args.days, args.weeks, args.months)
    print(f"대상 {len(names)}개 → 남김 {len(keep)}개, 정리 후보 {len(drop)}개, 날짜 못 읽음 {len(unknown)}개")
    print(f"규칙: 일 {args.days} · 주 {args.weeks} · 월 {args.months}")
    print("\n[남김]")
    for d, n in keep:
        print(f"  {d}  {n}  ({'/'.join(reasons[n])})")
    print("\n[정리 후보]")
    for d, n in drop:
        print(f"  {d}  {n}")
    if unknown:
        print("\n[날짜 못 읽음 - 건드리지 않음]")
        for n in unknown:
            print(f"  {n}")

    if not args.apply or args.list_file:
        print("\n미리보기입니다. 실제로 옮기려면 --folder 와 함께 --apply 를 붙이세요." if not args.list_file
              else "\n목록 파일 모드라 아무것도 옮기지 않았습니다.")
        return
    trash = args.trash if os.path.isabs(args.trash) else os.path.join(args.folder, args.trash)
    os.makedirs(trash, exist_ok=True)
    moved = 0
    for _, n in drop:
        dst = os.path.join(trash, n)
        if os.path.exists(dst):
            print(f"  [건너뜀] 휴지통에 같은 이름이 있음: {n}")
            continue
        shutil.move(os.path.join(args.folder, n), dst)
        moved += 1
    print(f"\n{moved}개를 {trash} 로 옮겼습니다. 확인 후 직접 지우세요.")


if __name__ == "__main__":
    main()
