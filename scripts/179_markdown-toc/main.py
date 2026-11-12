"""마크다운(.md) 문서의 제목(#, ##, ###)을 읽어 목차를 자동으로 만들고, 문서 안 표시 위치에 넣어 주는 스크립트.

생각의 흐름:
  1) 업무 매뉴얼·운영 가이드가 길어지면 목차가 필요한데, 제목을 바꿀 때마다 목차를 손으로 고치면 틀어집니다.
  2) 줄 맨 앞의 '#' 개수로 제목 단계를 알고, GitHub 방식으로 링크 주소(앵커)를 만듭니다.
     - 소문자로, 공백은 '-', 영문·숫자·한글·'-'·'_' 말고는 지웁니다. 같은 제목이 또 나오면 -1, -2 를 붙입니다.
  3) 코드 블록(``` 안) 속 '#' 은 제목이 아니므로 건너뜁니다.
  4) 문서에 <!-- toc --> 와 <!-- tocstop --> 표시가 있으면 그 사이를 새 목차로 바꿉니다.
     표시가 없으면 화면에만 보여 줍니다(문서는 건드리지 않음).
  5) 문서를 바꾸는 건 --apply 를 줄 때만 하고, 바꾸기 전 .bak 사본을 남깁니다.
"""
import argparse
import re
import shutil

HEAD_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
START, STOP = "<!-- toc -->", "<!-- tocstop -->"


def slug(text, used):
    s = re.sub(r"`|\*\*|__|\[|\]\([^)]*\)", "", text)      # 꾸밈 글자, 링크 주소 제거
    s = s.strip().lower()
    s = re.sub(r"[^\w\- 가-힣]", "", s)
    s = s.replace(" ", "-")
    base, n = s, used.get(s, 0)
    used[s] = n + 1
    return base if n == 0 else f"{base}-{n}"


def build_toc(lines, min_level, max_level):
    toc, used, in_code = [], {}, False
    for line in lines:
        if line.lstrip().startswith("```") or line.lstrip().startswith("~~~"):
            in_code = not in_code
            continue
        if in_code:
            continue
        m = HEAD_RE.match(line)
        if not m:
            continue
        level, title = len(m.group(1)), m.group(2)
        anchor = slug(title, used)       # 단계 밖 제목도 앵커 번호에는 영향을 주므로 먼저 계산
        if min_level <= level <= max_level:
            clean = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", title)
            toc.append(f"{'  ' * (level - min_level)}- [{clean}](#{anchor})")
    return toc


def main():
    ap = argparse.ArgumentParser(description="마크다운 목차 자동 생성")
    ap.add_argument("file", help="마크다운 파일")
    ap.add_argument("--min", type=int, default=2, help="목차에 넣을 가장 큰 제목 단계 (기본 2 = ##)")
    ap.add_argument("--max", type=int, default=3, help="목차에 넣을 가장 작은 제목 단계 (기본 3 = ###)")
    ap.add_argument("--apply", action="store_true", help="<!-- toc --> 표시 사이에 목차를 실제로 넣습니다")
    args = ap.parse_args()

    with open(args.file, encoding="utf-8") as f:
        text = f.read()
    lines = text.splitlines()
    toc = build_toc(lines, args.min, args.max)
    print(f"제목 {len(toc)}개로 목차를 만들었습니다 (단계 {args.min}~{args.max})\n")
    print("\n".join(toc))

    if START not in text or STOP not in text:
        print(f"\n문서에 {START} 와 {STOP} 표시가 없어 화면에만 보여 줍니다. 넣고 싶은 곳에 두 줄을 적어 주세요.")
        return
    s, e = text.index(START), text.index(STOP)
    new_text = text[:s + len(START)] + "\n" + "\n".join(toc) + "\n" + text[e:]
    if new_text == text:
        print("\n목차가 이미 최신입니다. 바꿀 것이 없습니다.")
        return
    if not args.apply:
        print(f"\n[미리보기] 문서의 목차가 바뀔 예정입니다. 실제로 넣으려면 --apply 를 붙이세요.")
        return
    shutil.copy2(args.file, args.file + ".bak")
    with open(args.file, "w", encoding="utf-8") as f:
        f.write(new_text)
    print(f"\n목차를 넣었습니다 → {args.file} (원본 사본: {args.file}.bak)")


if __name__ == "__main__":
    main()
