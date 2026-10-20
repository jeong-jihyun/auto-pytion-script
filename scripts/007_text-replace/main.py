"""텍스트 일괄 치환 스크립트.

폴더 안의 텍스트 파일들에서 단어를 한꺼번에 바꿉니다.
규칙 파일(CSV: 바꿀말,새말)을 읽어 적용합니다.
기본은 --dry-run: 몇 군데 바뀔지만 보여주고 파일은 건드리지 않습니다.
--apply 를 쓰면 원본은 .bak 으로 남기고 수정합니다.
"""
import argparse
import csv
from pathlib import Path


def 규칙읽기(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as fp:
        return [(r[0], r[1]) for r in csv.reader(fp) if len(r) >= 2 and r[0]]


def main():
    p = argparse.ArgumentParser(description="텍스트 파일 일괄 치환")
    p.add_argument("folder", type=Path)
    p.add_argument("--rules", type=Path, required=True, help="규칙 CSV (바꿀말,새말)")
    p.add_argument("--ext", default=".txt", help="대상 확장자 (기본 .txt)")
    p.add_argument("--apply", action="store_true")
    a = p.parse_args()
    rules = 규칙읽기(a.rules)
    total = 0
    for f in sorted(a.folder.glob(f"*{a.ext}")):
        text = f.read_text(encoding="utf-8")
        new, n = text, 0
        for old, rep in rules:
            n += new.count(old)
            new = new.replace(old, rep)
        if n:
            print(f"{'수정' if a.apply else '[미리보기]'} {f.name}: {n}군데")
            if a.apply:
                f.with_suffix(f.suffix + ".bak").write_text(text, encoding="utf-8")
                f.write_text(new, encoding="utf-8")
        total += n
    print(f"총 {total}군데")


if __name__ == "__main__":
    main()
