"""원본 폴더의 새 파일·바뀐 파일만 대상 폴더로 복사하는(한 방향 동기화) 스크립트.

생각의 흐름:
  1) 공유 폴더·USB·NAS로 자료를 옮길 때 매번 전체를 복사하면 오래 걸리고, 무엇이 바뀌었는지 모릅니다.
  2) 원본(src)의 파일을 하나씩 대상(dst)의 같은 위치 파일과 비교합니다.
       새파일 : 대상에 없음 → 복사
       바뀜   : 내용이 다름 → 복사(덮기 전에 대상의 옛 파일은 _mirror_backup/날짜시간/ 에 보관)
       충돌   : 내용이 다른데 대상 쪽이 더 최근에 고쳐짐 → 누가 대상에서 직접 고쳤을 수 있으니 건너뛰고 알림
       같음   : 그대로 둠
     비교는 기본이 '내용 해시(SHA-256)'라 정확하고, --quick 이면 크기+수정시각만 봐서 빠릅니다.
  3) 원본에 없고 대상에만 있는 파일은 '대상에만 있음'으로 알려 주기만 하고 절대 지우지 않습니다.
  4) 기본은 미리보기(dry-run). --apply 를 붙여야 실제로 복사합니다. 수정시각은 원본 그대로 유지(copy2).
"""
import argparse
import csv
import hashlib
import shutil
from datetime import datetime
from pathlib import Path

BACKUP_DIR = "_mirror_backup"


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def same(src, dst, quick):
    s, d = src.stat(), dst.stat()
    if s.st_size != d.st_size:
        return False
    if quick:
        return abs(s.st_mtime - d.st_mtime) < 2  # FAT/NAS 는 시각 오차가 2초까지 남
    return sha(src) == sha(dst)


def main():
    p = argparse.ArgumentParser(description="새 파일·바뀐 파일만 한 방향 복사(삭제 안 함, 미리보기 기본)")
    p.add_argument("src", type=Path, help="원본 폴더")
    p.add_argument("dst", type=Path, help="대상 폴더")
    p.add_argument("--quick", action="store_true", help="크기+수정시각만 비교(빠름)")
    p.add_argument("--exclude", nargs="*", default=["~$*", "*.tmp", "Thumbs.db", ".DS_Store"], help="뺄 파일 패턴")
    p.add_argument("--apply", action="store_true", help="실제로 복사")
    p.add_argument("--report", type=Path, default=Path("output/mirror_report.csv"))
    a = p.parse_args()

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    rows = []
    src_files = set()
    for f in sorted(a.src.rglob("*")):
        rel = f.relative_to(a.src)
        if not f.is_file() or rel.parts[0] == BACKUP_DIR or any(f.match(pt) for pt in a.exclude):
            continue
        src_files.add(rel)
        t = a.dst / rel
        if not t.exists():
            state = "새파일"
        elif same(f, t, a.quick):
            state = "같음"
        elif t.stat().st_mtime > f.stat().st_mtime + 2:
            state = "충돌"
        else:
            state = "바뀜"
        if a.apply and state in ("새파일", "바뀜"):
            t.parent.mkdir(parents=True, exist_ok=True)
            if state == "바뀜":
                bak = a.dst / BACKUP_DIR / stamp / rel
                bak.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(t, bak)
            shutil.copy2(f, t)
        rows.append([state, str(rel), f.stat().st_size])
    if a.dst.exists():
        for t in sorted(a.dst.rglob("*")):
            rel = t.relative_to(a.dst)
            if t.is_file() and rel.parts[0] != BACKUP_DIR and rel not in src_files:
                rows.append(["대상에만있음", str(rel), t.stat().st_size])

    mode = "실제 복사" if a.apply else "미리보기(dry-run)"
    print(f"== {mode}: {a.src} -> {a.dst} ({'크기+시각' if a.quick else '내용 해시'} 비교) ==")
    for state, rel, size in rows:
        if state != "같음":
            print(f"  [{state}] {rel} ({size:,} bytes)")
    cnt = {k: sum(1 for r in rows if r[0] == k) for k in ["새파일", "바뀜", "충돌", "같음", "대상에만있음"]}
    print("요약: " + ", ".join(f"{k} {v}" for k, v in cnt.items()))
    if cnt["충돌"]:
        print("※ 충돌 파일은 대상 쪽이 더 최근에 고쳐져 건너뛰었습니다. 직접 확인하세요.")
    if not a.apply and (cnt["새파일"] or cnt["바뀜"]):
        print("실제로 복사하려면 --apply 를 붙이세요. (바뀐 파일의 옛 버전은 대상/_mirror_backup/ 에 보관)")
    a.report.parent.mkdir(parents=True, exist_ok=True)
    with a.report.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["상태", "상대경로", "크기"])
        w.writerows(rows)


if __name__ == "__main__":
    main()
