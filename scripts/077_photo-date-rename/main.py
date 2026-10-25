"""사진 파일 이름을 촬영 날짜(EXIF) 기준 'YYYYMMDD_HHMMSS.jpg'로 바꾸는 스크립트.

현장 사진·영수증 사진이 IMG_1234.jpg 처럼 섞여 있으면 찾기 어렵습니다.
생각의 흐름:
  1) 사진 안의 EXIF '촬영 일시(DateTimeOriginal)'를 읽습니다.
  2) 없으면 --fallback mtime 일 때만 파일 수정 시각을 씁니다(기본은 건너뜀).
  3) 같은 시각 사진이 여러 장이면 _1, _2 를 붙여 덮어쓰지 않게 합니다.
  4) 기본은 미리보기(dry-run). --apply 를 붙여야 실제로 이름을 바꿉니다.
"""
import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Pillow가 필요합니다: pip install -r requirements.txt")
    sys.exit(1)

EXTS = {".jpg", ".jpeg", ".tif", ".tiff", ".png", ".heic"}
DATETIME_ORIGINAL = 36867
DATETIME = 306


def shot_time(path):
    try:
        with Image.open(path) as im:
            exif = im.getexif()
            value = exif.get_ifd(0x8769).get(DATETIME_ORIGINAL) or exif.get(DATETIME)
    except Exception:
        return None
    if not value:
        return None
    try:
        return datetime.strptime(str(value).strip(), "%Y:%m:%d %H:%M:%S")
    except ValueError:
        return None


def main():
    p = argparse.ArgumentParser(description="사진 이름을 촬영일시로 변경")
    p.add_argument("folder", type=Path)
    p.add_argument("--prefix", default="", help="이름 앞에 붙일 말(예: 현장A_)")
    p.add_argument("--fallback", choices=["skip", "mtime"], default="skip", help="EXIF가 없을 때")
    p.add_argument("--apply", action="store_true", help="실제로 이름 변경(없으면 미리보기)")
    p.add_argument("--log", type=Path, default=Path("output/rename_log.csv"))
    a = p.parse_args()

    files = sorted(f for f in a.folder.iterdir() if f.is_file() and f.suffix.lower() in EXTS)
    taken = {f.name for f in a.folder.iterdir()}
    plan = []
    for f in files:
        t = shot_time(f)
        source = "EXIF"
        if t is None:
            if a.fallback == "mtime":
                t, source = datetime.fromtimestamp(f.stat().st_mtime), "수정시각"
            else:
                plan.append((f, None, "촬영일시 없음 → 건너뜀"))
                continue
        base = f"{a.prefix}{t:%Y%m%d_%H%M%S}"
        ext = f.suffix.lower()
        new, n = base + ext, 1
        if new == f.name:
            plan.append((f, None, "이미 바른 이름"))
            continue
        while new in taken:
            new = f"{base}_{n}{ext}"
            n += 1
        taken.discard(f.name)
        taken.add(new)
        plan.append((f, a.folder / new, source))

    a.log.parent.mkdir(parents=True, exist_ok=True)
    with a.log.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["원래이름", "새이름", "근거", "실행"])
        for old, new, note in plan:
            done = ""
            if new is not None and a.apply:
                old.rename(new)
                done = "변경함"
            w.writerow([old.name, new.name if new else "", note, done or ("미리보기" if new else "")])
            print(f"{old.name} → {new.name if new else '-'} ({note})")
    changes = sum(1 for _, n, _ in plan if n)
    mode = "변경 완료" if a.apply else "미리보기(실제로 바꾸려면 --apply)"
    print(f"\n대상 {len(files)}개 중 바꿀 것 {changes}개 · {mode} · 기록 {a.log}")


if __name__ == "__main__":
    main()
