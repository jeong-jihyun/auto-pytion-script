"""폴더 백업 스크립트.

폴더를 날짜·시간이 붙은 zip 파일로 백업하고, 오래된 백업은 개수 기준으로 정리합니다.
- 기본은 --dry-run(무엇을 할지 보여주기만).
- --apply 를 쓰면 zip 생성. 오래된 백업 삭제는 --keep N 을 줬을 때만, 그리고 --apply 일 때만 합니다.
- 삭제 대상은 '백업이름_YYYYMMDD_HHMMSS.zip' 형식으로 이 스크립트가 만든 파일만입니다.
"""
import argparse
import re
import zipfile
from datetime import datetime
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description="폴더 zip 백업")
    p.add_argument("source", type=Path)
    p.add_argument("-o", "--output", type=Path, default=Path("backup_out"))
    p.add_argument("--keep", type=int, help="남길 최근 백업 개수 (이보다 오래된 것은 삭제)")
    p.add_argument("--apply", action="store_true")
    a = p.parse_args()
    name = a.source.resolve().name
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = a.output / f"{name}_{stamp}.zip"
    files = [f for f in sorted(a.source.rglob("*")) if f.is_file()]
    print(f"{'백업 생성' if a.apply else '[미리보기] 백업 예정'}: {target} (파일 {len(files)}개)")
    if a.apply:
        a.output.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
            for f in files:
                z.write(f, f.relative_to(a.source))
        with zipfile.ZipFile(target) as z:
            assert z.testzip() is None, "zip 검사 실패"
        print("zip 무결성 확인 완료")
    if a.keep is not None and a.output.exists():
        pat = re.compile(rf"^{re.escape(name)}_\d{{8}}_\d{{6}}\.zip$")
        old = sorted(f for f in a.output.iterdir() if pat.match(f.name))
        # 방금 만든 것(또는 만들 것)을 포함해 keep 개만 남김
        n_after = len(old) + (0 if a.apply else 1)
        for f in old[: max(0, n_after - a.keep)]:
            print(f"{'삭제' if a.apply else '[미리보기] 삭제 예정'}: {f.name}")
            if a.apply:
                f.unlink()


if __name__ == "__main__":
    main()
