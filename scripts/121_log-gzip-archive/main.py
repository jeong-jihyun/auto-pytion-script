"""오래된 로그 파일을 gzip(.gz)으로 압축해 디스크를 아끼는 스크립트.

생각의 흐름:
  1) 서버·배치 로그는 매일 쌓여 디스크를 채웁니다. 지우면 나중에 장애 분석을 못 하니 '압축'이 안전합니다.
  2) 로그가 며칠 된 것인지는 파일 이름 속 날짜(app-2026-10-01.log, batch_20261001.log)로 먼저 판단하고,
     이름에 날짜가 없으면 파일 수정일로 판단합니다. (복사·내려받기를 하면 수정일이 바뀌기 때문에 이름이 더 믿을 만합니다)
  3) 기준 일수(--days)보다 오래된 파일만 고릅니다. 오늘 쓰는 로그는 절대 건드리지 않습니다.
  4) 기본은 미리보기(dry-run)입니다. --apply 를 붙여야 실제로 .gz 를 만들고,
     압축본을 다시 풀어 원본과 내용이 같은지 확인(검증)한 뒤에만 원본을 지웁니다.
     --keep 을 주면 원본을 남깁니다.
"""
import argparse
import gzip
import hashlib
import re
import shutil
from datetime import date, datetime
from pathlib import Path

DATE_PATTERNS = [
    re.compile(r"(\d{4})-(\d{2})-(\d{2})"),
    re.compile(r"(\d{4})(\d{2})(\d{2})"),
]


def date_from_name(name):
    """파일 이름에서 날짜를 찾습니다. 없으면 None."""
    for pat in DATE_PATTERNS:
        m = pat.search(name)
        if m:
            try:
                return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            except ValueError:
                continue
    return None


def sha256_of(path, opener=open):
    h = hashlib.sha256()
    with opener(path, "rb") as fp:
        for chunk in iter(lambda: fp.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def human(n):
    for unit in ["B", "KB", "MB", "GB"]:
        if n < 1024:
            return f"{n:.0f}{unit}" if unit == "B" else f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"


def main():
    p = argparse.ArgumentParser(description="오래된 로그 gzip 압축(미리보기 기본)")
    p.add_argument("folder", type=Path, help="로그 폴더")
    p.add_argument("--days", type=int, default=7, help="이 일수보다 오래된 로그만 압축(기본 7)")
    p.add_argument("--pattern", default="*.log", help="대상 파일 패턴(기본 *.log)")
    p.add_argument("--recursive", action="store_true", help="하위 폴더까지")
    p.add_argument("--today", help="기준일 YYYY-MM-DD(기본 오늘, 테스트용)")
    p.add_argument("--keep", action="store_true", help="압축 후 원본을 남김")
    p.add_argument("--apply", action="store_true", help="실제로 압축(없으면 미리보기)")
    a = p.parse_args()

    today = datetime.strptime(a.today, "%Y-%m-%d").date() if a.today else date.today()
    files = sorted(a.folder.rglob(a.pattern) if a.recursive else a.folder.glob(a.pattern))

    targets, before, skipped = [], 0, 0
    for f in files:
        if not f.is_file() or f.suffix == ".gz":
            continue
        d = date_from_name(f.name)
        basis = "이름"
        if d is None:
            d = datetime.fromtimestamp(f.stat().st_mtime).date()
            basis = "수정일"
        age = (today - d).days
        if age <= a.days:
            skipped += 1
            continue
        gz = f.with_name(f.name + ".gz")
        if gz.exists():
            print(f"[건너뜀] 이미 압축본이 있음: {gz.name}")
            continue
        targets.append((f, gz, age, basis))
        before += f.stat().st_size

    mode = "실제 압축" if a.apply else "미리보기(dry-run)"
    print(f"== {mode} | 기준일 {today} | {a.days}일 초과 대상 {len(targets)}개, 그대로 둠 {skipped}개 ==")
    after = 0
    for f, gz, age, basis in targets:
        if not a.apply:
            print(f"  압축 예정: {f.name} ({age}일 전, {basis} 기준, {human(f.stat().st_size)})")
            continue
        with f.open("rb") as src, gzip.open(gz, "wb") as dst:
            shutil.copyfileobj(src, dst)
        # 검증: 압축을 다시 푼 내용의 해시가 원본과 같아야 원본을 지웁니다.
        if sha256_of(f) != sha256_of(gz, gzip.open):
            gz.unlink()
            print(f"  [오류] 검증 실패, 원본 유지: {f.name}")
            continue
        after += gz.stat().st_size
        print(f"  압축 완료: {f.name} -> {gz.name} ({human(f.stat().st_size)} -> {human(gz.stat().st_size)})")
        if not a.keep:
            f.unlink()
    if a.apply and targets:
        print(f"합계: {human(before)} -> {human(after)} (약 {human(before - after)} 절약)")
    elif targets:
        print(f"압축하면 원본 합계 {human(before)} 를 줄일 수 있습니다. 실제로 하려면 --apply 를 붙이세요.")


if __name__ == "__main__":
    main()
