"""폴더 안의 zip 파일을 한꺼번에 풀어 주는 스크립트.

- zip 하나마다 '압축파일이름' 폴더를 따로 만들어 그 안에 풉니다(파일이 뒤섞이지 않게).
- 보안: zip 안에 '../' 처럼 밖으로 나가려는 경로가 있으면 그 파일은 건너뜁니다(zip slip 방지).
- 기본은 미리보기(--dry-run 효과). 실제로 풀려면 --apply 를 붙입니다.
- 이미 풀려 있는 폴더가 있으면 덮어쓰지 않고 건너뜁니다.
"""
import argparse
import zipfile
from pathlib import Path


def safe_target(base: Path, name: str):
    """zip 안 경로가 base 폴더 밖으로 나가지 않으면 실제 경로를, 아니면 None 을 돌려줍니다."""
    target = (base / name).resolve()
    try:
        target.relative_to(base.resolve())
    except ValueError:
        return None
    return target


def main():
    p = argparse.ArgumentParser(description="폴더 안 zip 일괄 풀기")
    p.add_argument("folder", type=Path, help="zip 파일이 들어 있는 폴더")
    p.add_argument("-o", "--output", type=Path, default=Path("output/unzipped"), help="풀 위치")
    p.add_argument("--apply", action="store_true", help="실제로 풉니다(없으면 미리보기만)")
    a = p.parse_args()

    zips = sorted(a.folder.glob("*.zip"))
    if not zips:
        print("zip 파일이 없습니다.")
        return
    total_files = 0
    for z in zips:
        dest = a.output / z.stem
        # 1) 이미 있으면 건너뜁니다(덮어쓰기 방지).
        if dest.exists():
            print(f"[건너뜀] {z.name}: {dest} 폴더가 이미 있습니다")
            continue
        try:
            zf = zipfile.ZipFile(z)
        except zipfile.BadZipFile:
            print(f"[오류] {z.name}: 깨진 zip 파일입니다")
            continue
        with zf:
            names = [n for n in zf.namelist() if not n.endswith("/")]
            ok, bad = [], []
            for n in names:
                (ok if safe_target(dest, n) else bad).append(n)
            print(f"[{'풀기' if a.apply else '미리보기'}] {z.name}: 파일 {len(ok)}개"
                  + (f", 위험 경로 {len(bad)}개 건너뜀" if bad else ""))
            for n in bad:
                print(f"    위험 경로 무시: {n}")
            if a.apply:
                for n in ok:
                    t = safe_target(dest, n)
                    t.parent.mkdir(parents=True, exist_ok=True)
                    t.write_bytes(zf.read(n))
            total_files += len(ok)
    print(f"합계: zip {len(zips)}개, 파일 {total_files}개" + ("" if a.apply else " (미리보기: --apply 를 붙이면 실제로 풉니다)"))


if __name__ == "__main__":
    main()
