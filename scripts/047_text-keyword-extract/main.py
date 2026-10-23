"""폴더의 텍스트·로그 파일에서 키워드가 들어 있는 줄만 뽑아 CSV로 모으는 스크립트 (grep 같은 것).

결과 CSV 열: 파일, 줄번호, 줄내용
- --keyword 는 여러 번 쓸 수 있고, 하나라도 들어 있으면 뽑습니다.
- --ignore-case 로 대소문자 구분을 없앨 수 있습니다.
- 인코딩은 utf-8 을 먼저 시도하고 안 되면 cp949 로 읽습니다.
"""
import argparse
import csv
from pathlib import Path


def read_lines(path: Path):
    """파일을 utf-8, 안 되면 cp949 로 읽어 줄 목록을 돌려줍니다."""
    for enc in ("utf-8-sig", "cp949"):
        try:
            return path.read_text(encoding=enc).splitlines()
        except UnicodeDecodeError:
            continue
    return []


def main():
    p = argparse.ArgumentParser(description="키워드 줄 추출")
    p.add_argument("folder", type=Path)
    p.add_argument("-k", "--keyword", action="append", required=True, help="찾을 글자(여러 번 가능)")
    p.add_argument("--ext", default=".txt,.log", help="검사할 확장자(쉼표 구분)")
    p.add_argument("-i", "--ignore-case", action="store_true")
    p.add_argument("-o", "--output", type=Path, default=Path("output/hits.csv"))
    a = p.parse_args()

    exts = tuple(e.strip().lower() for e in a.ext.split(","))
    keys = [k.lower() for k in a.keyword] if a.ignore_case else a.keyword
    hits, files = [], 0
    for f in sorted(a.folder.rglob("*")):
        if not f.is_file() or f.suffix.lower() not in exts:
            continue
        files += 1
        for no, line in enumerate(read_lines(f), start=1):
            target = line.lower() if a.ignore_case else line
            if any(k in target for k in keys):
                hits.append([str(f.relative_to(a.folder)), no, line.strip()])
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["파일", "줄번호", "줄내용"])
        w.writerows(hits)
    print(f"파일 {files}개 검사, {len(hits)}줄 발견 -> {a.output}")
    for h in hits[:10]:
        print("  ", *h)


if __name__ == "__main__":
    main()
