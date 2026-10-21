"""오래된 파일 정리 스크립트.

폴더 안에서 마지막 수정일이 N일보다 오래된 파일을 찾아,
삭제하지 않고 '보관 폴더(--trash)'로 옮깁니다. (실수해도 되돌릴 수 있게)
기본은 미리보기(dry-run)이고, --apply 를 붙여야 실제로 옮깁니다.
"""
import argparse
import shutil
import time
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description="오래된 파일을 보관 폴더로 이동")
    p.add_argument("folder", type=Path, help="검사할 폴더")
    p.add_argument("--days", type=int, required=True, help="이 일수보다 오래된 파일이 대상")
    p.add_argument("--pattern", default="*", help="대상 파일 이름 패턴 (예: *.log)")
    p.add_argument("--trash", type=Path, default=Path("old_files_out"), help="옮길 보관 폴더")
    p.add_argument("--apply", action="store_true", help="실제로 옮김 (없으면 미리보기만)")
    a = p.parse_args()

    if not a.folder.is_dir():
        raise SystemExit(f"오류: 폴더가 아닙니다: {a.folder}")
    limit = time.time() - a.days * 86400
    trash = a.trash.resolve()
    targets = []
    for f in sorted(a.folder.rglob(a.pattern)):
        # 보관 폴더 안의 파일은 다시 검사하지 않습니다
        if f.is_file() and trash not in f.resolve().parents and f.stat().st_mtime < limit:
            targets.append(f)

    total = 0
    for f in targets:
        st = f.stat()
        total += st.st_size
        day = time.strftime("%Y-%m-%d", time.localtime(st.st_mtime))
        print(f"  [{'이동' if a.apply else '대상'}] {f}  (수정일 {day}, {st.st_size}바이트)")
        if a.apply:
            dest = trash / f.relative_to(a.folder)
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():  # 같은 이름이 있으면 덮어쓰지 않고 번호를 붙임
                n = 1
                while dest.with_name(f"{dest.stem}_{n}{dest.suffix}").exists():
                    n += 1
                dest = dest.with_name(f"{dest.stem}_{n}{dest.suffix}")
            shutil.move(str(f), str(dest))
    mode = "이동 완료" if a.apply else "미리보기(실제 변경 없음, --apply 로 실행)"
    print(f"{a.days}일보다 오래된 파일 {len(targets)}개, 합계 {total}바이트 - {mode}")


if __name__ == "__main__":
    main()
