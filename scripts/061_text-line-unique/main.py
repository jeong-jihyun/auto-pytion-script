"""텍스트 파일의 줄을 정리하는 스크립트: 중복 줄 제거, 정렬, 줄별 등장 횟수 세기.

예) 이메일 주소 목록·품목 코드 목록처럼 한 줄에 하나씩 적힌 목록을 깔끔하게 만들 때 씁니다.
원본 파일은 바꾸지 않고 새 파일로 저장합니다.
"""
import argparse
import sys
from collections import Counter
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description="텍스트 줄 중복 제거·정렬·횟수 세기")
    p.add_argument("input", type=Path, help="입력 텍스트 파일")
    p.add_argument("-o", "--output", type=Path, default=Path("output/lines.txt"))
    p.add_argument("--sort", action="store_true", help="가나다/ABC 순으로 정렬")
    p.add_argument("--ignore-case", action="store_true", help="대소문자를 같은 글자로 봄")
    p.add_argument("--count", action="store_true", help="줄 앞에 등장 횟수를 붙임(많이 나온 순)")
    p.add_argument("--keep-blank", action="store_true", help="빈 줄도 남김(기본은 빈 줄 제거)")
    a = p.parse_args()

    if not a.input.is_file():
        print(f"[오류] 파일이 없습니다: {a.input}")
        sys.exit(1)

    # utf-8(BOM 포함)로 읽고, 줄 끝 공백은 지웁니다.
    lines = [x.strip() for x in a.input.read_text(encoding="utf-8-sig").splitlines()]
    if not a.keep_blank:
        lines = [x for x in lines if x]

    # 비교용 키(대소문자 무시 옵션이면 소문자로 바꿔 비교), 처음 나온 모양을 보여 줌
    key = (lambda s: s.lower()) if a.ignore_case else (lambda s: s)
    counter = Counter(key(x) for x in lines)
    first = {}
    for x in lines:
        first.setdefault(key(x), x)

    keys = list(first)  # 처음 나온 순서 유지
    if a.count:
        keys.sort(key=lambda k: (-counter[k], first[k]))
    elif a.sort:
        keys.sort(key=lambda k: first[k])

    out = [f"{counter[k]}\t{first[k]}" if a.count else first[k] for k in keys]
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"입력 {len(lines)}줄 → 고유 {len(keys)}줄 (중복 {len(lines) - len(keys)}줄 제거)")
    print(f"저장: {a.output}")


if __name__ == "__main__":
    main()
