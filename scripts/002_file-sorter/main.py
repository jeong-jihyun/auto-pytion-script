"""폴더 파일 자동 분류 스크립트.

파일 확장자를 보고 '문서/이미지/표/압축/기타' 폴더로 옮깁니다.
기본은 --dry-run(미리보기)이라 실제로 옮기지 않습니다.
실제로 옮기려면 --apply 를 붙이세요. 같은 이름이 있으면 덮어쓰지 않고 번호를 붙입니다.
"""
import argparse
import shutil
from pathlib import Path

분류표 = {
    "문서": {".pdf", ".doc", ".docx", ".txt", ".hwp", ".md"},
    "이미지": {".jpg", ".jpeg", ".png", ".gif", ".bmp"},
    "표": {".xls", ".xlsx", ".csv"},
    "압축": {".zip", ".7z", ".tar", ".gz"},
}


def 분류(path: Path) -> str:
    ext = path.suffix.lower()
    for 이름, 확장자들 in 분류표.items():
        if ext in 확장자들:
            return 이름
    return "기타"


def 겹치지않는_경로(dest: Path) -> Path:
    if not dest.exists():
        return dest
    i = 1
    while True:
        cand = dest.with_name(f"{dest.stem}_{i}{dest.suffix}")
        if not cand.exists():
            return cand
        i += 1


def main():
    p = argparse.ArgumentParser(description="확장자별 파일 자동 분류")
    p.add_argument("source", type=Path, help="정리할 폴더")
    p.add_argument("-o", "--output", type=Path, help="분류 결과를 둘 폴더 (기본: source 안)")
    p.add_argument("--apply", action="store_true", help="실제로 이동 (없으면 미리보기만)")
    a = p.parse_args()
    dest_root = a.output or a.source
    count = 0
    for f in sorted(a.source.iterdir()):
        if not f.is_file():
            continue
        dest = 겹치지않는_경로(dest_root / 분류(f) / f.name)
        print(f"{'이동' if a.apply else '[미리보기]'} {f.name} -> {dest.relative_to(dest_root)}")
        if a.apply:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(f), str(dest))
        count += 1
    print(f"총 {count}개 처리" + ("" if a.apply else " (미리보기: 실제 이동 없음)"))


if __name__ == "__main__":
    main()
