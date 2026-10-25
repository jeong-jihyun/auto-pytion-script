"""문서 폴더의 마크다운(.md) 파일에서 깨진 '내부 링크'와 '그림 경로'를 찾는 스크립트.

생각의 흐름:
  1) 폴더 안 .md 파일을 모두 읽고 [글자](주소), ![그림](주소) 형식의 링크를 뽑습니다.
     코드 블록(```) 안의 내용은 예시일 뿐이므로 건너뜁니다.
  2) http(s)://, mailto: 같은 외부 링크는 인터넷에 접속하지 않고 '외부'로만 셉니다.
  3) 상대 경로 링크는 그 .md 파일 위치를 기준으로 실제 파일이 있는지 확인합니다.
  4) 'guide.md#설치' 처럼 # 뒤 제목(앵커)이 있으면, 대상 문서에 그 제목이 실제로 있는지도 봅니다.
     제목 → 앵커 변환은 GitHub 방식(소문자, 공백→-, 문장부호 제거)을 따릅니다.
"""
import argparse
import csv
import re
from pathlib import Path
from urllib.parse import unquote

LINK = re.compile(r"(!?)\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
HEAD = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$")


def anchor(title):
    t = re.sub(r"[^\w\- ]", "", title.strip().lower())
    return t.replace(" ", "-")


def anchors_of(path, cache):
    if path not in cache:
        found, in_code = set(), False
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.strip().startswith("```"):
                in_code = not in_code
                continue
            m = HEAD.match(line)
            if m and not in_code:
                found.add(anchor(m.group(1)))
        cache[path] = found
    return cache[path]


def main():
    p = argparse.ArgumentParser(description="마크다운 내부 링크 점검")
    p.add_argument("folder", type=Path)
    p.add_argument("-o", "--output", type=Path, default=Path("output/md_links.csv"))
    a = p.parse_args()

    cache, rows, external = {}, [], 0
    md_files = sorted(a.folder.rglob("*.md"))
    for md in md_files:
        in_code = False
        for no, line in enumerate(md.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if line.strip().startswith("```"):
                in_code = not in_code
                continue
            if in_code:
                continue
            for img, text, url in LINK.findall(line):
                if re.match(r"^[a-z]+:", url, re.I):
                    external += 1
                    continue
                path_part, _, frag = url.partition("#")
                target = md if not path_part else (md.parent / unquote(path_part)).resolve()
                kind = "그림" if img else "링크"
                if path_part and not target.exists():
                    rows.append([str(md.relative_to(a.folder)), no, kind, url, "파일 없음"])
                elif frag and target.suffix.lower() == ".md" and anchor(unquote(frag)) not in anchors_of(target, cache):
                    rows.append([str(md.relative_to(a.folder)), no, kind, url, "제목(앵커) 없음"])
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["문서", "줄", "종류", "주소", "문제"])
        w.writerows(rows)
    print(f"마크다운 {len(md_files)}개 점검, 깨진 링크 {len(rows)}개, 외부 링크 {external}개(확인 안 함) → {a.output}")
    for r in rows:
        print(f"  - {r[0]}:{r[1]} {r[2]} {r[3]} → {r[4]}")


if __name__ == "__main__":
    main()
