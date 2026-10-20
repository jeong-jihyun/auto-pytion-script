"""파일 이름 일괄 변경 스크립트.

폴더 안 파일 이름 앞에 접두어를 붙이거나, 일련번호(001, 002...)를 붙이거나,
특정 글자를 다른 글자로 바꿉니다. 기본은 --dry-run(미리보기)입니다.
"""
import argparse
from pathlib import Path


def 새이름(f: Path, i: int, a) -> str:
    stem = f.stem
    if a.find:
        stem = stem.replace(a.find, a.replace)
    if a.number:
        stem = f"{i:03d}_{stem}"
    return f"{a.prefix}{stem}{f.suffix}"


def main():
    p = argparse.ArgumentParser(description="파일 이름 일괄 변경")
    p.add_argument("folder", type=Path)
    p.add_argument("--prefix", default="", help="앞에 붙일 글자")
    p.add_argument("--find", default="", help="바꿀 글자")
    p.add_argument("--replace", default="", help="새 글자")
    p.add_argument("--number", action="store_true", help="일련번호 붙이기")
    p.add_argument("--apply", action="store_true", help="실제로 변경 (없으면 미리보기)")
    a = p.parse_args()
    files = sorted(x for x in a.folder.iterdir() if x.is_file())
    plan = [(f, f.with_name(새이름(f, i, a))) for i, f in enumerate(files, 1)]
    # 이름이 겹치면 덮어쓰기 위험 -> 중단
    names = [n.name for _, n in plan]
    if len(set(names)) != len(names):
        print("오류: 바뀐 이름이 서로 겹칩니다. 옵션을 바꿔 주세요.")
        raise SystemExit(1)
    existing = {x.name for x in files}
    for old, new in plan:
        if old == new:
            continue
        if new.exists() and new.name not in existing:
            print(f"[건너뜀] {new.name} 이미 있음")
            continue
        print(f"{'변경' if a.apply else '[미리보기]'} {old.name} -> {new.name}")
        if a.apply:
            old.rename(new)


if __name__ == "__main__":
    main()
