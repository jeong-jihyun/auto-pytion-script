"""이메일 본문 일괄 생성 스크립트 (발송은 하지 않습니다).

받는 사람 목록(CSV)과 본문 틀(txt)을 합쳐서, 사람마다 이메일 본문 파일을 만듭니다.
- 틀 안의 {이름}, {회사} 처럼 중괄호로 쓴 부분이 CSV의 같은 이름 열 값으로 바뀝니다.
- 틀 첫 줄이 '제목: ...' 이면 제목으로 쓰고, 파일 맨 위에 적어 줍니다.
- 틀에 쓴 이름이 CSV에 없으면 한 건도 만들지 않고 알려 줍니다.
만든 파일은 눈으로 확인한 뒤 직접 복사해서 보내세요. 메일을 보내는 기능은 일부러 넣지 않았습니다.
"""
import argparse
import csv
import re
import string
import sys
from pathlib import Path


def 안전한_파일이름(글):
    return re.sub(r'[\\/:*?"<>|\s]+', "_", 글).strip("_") or "noname"


def main():
    p = argparse.ArgumentParser(description="CSV + 틀 -> 이메일 본문 파일")
    p.add_argument("recipients", help="받는 사람 CSV (머리글 필수)")
    p.add_argument("template", help="본문 틀 txt")
    p.add_argument("-o", "--output", default="output/emails", help="결과 폴더")
    p.add_argument("--name-col", default="이름", help="파일 이름에 쓸 열 (기본: 이름)")
    p.add_argument("--encoding", default="utf-8-sig")
    a = p.parse_args()

    틀 = Path(a.template).read_text(encoding="utf-8")
    줄들 = 틀.splitlines()
    제목틀 = ""
    if 줄들 and 줄들[0].startswith("제목:"):
        제목틀 = 줄들[0][3:].strip()
        본문틀 = "\n".join(줄들[1:]).lstrip("\n")
    else:
        본문틀 = 틀

    # 틀에서 쓰는 이름표({이름} 등)를 모두 찾습니다.
    필요한 = {f for _, f, _, _ in string.Formatter().parse(제목틀 + "\n" + 본문틀) if f}
    with open(a.recipients, newline="", encoding=a.encoding) as fp:
        읽기 = csv.DictReader(fp)
        없는 = 필요한 - set(읽기.fieldnames or [])
        if 없는:
            print(f"[오류] 틀에서 쓰는 {sorted(없는)} 열이 CSV에 없습니다. CSV 열: {읽기.fieldnames}")
            return 1
        사람들 = list(읽기)
    if not 사람들:
        print("받는 사람이 없습니다.")
        return 1

    out = Path(a.output)
    out.mkdir(parents=True, exist_ok=True)
    for i, 행 in enumerate(사람들, start=1):
        제목 = 제목틀.format_map(행)
        본문 = 본문틀.format_map(행)
        이름 = 안전한_파일이름(행.get(a.name_col, "") or f"row{i}")
        경로 = out / f"{i:03d}_{이름}.txt"
        경로.write_text(f"제목: {제목}\n\n{본문.rstrip()}\n", encoding="utf-8")
    print(f"완료: 이메일 본문 {len(사람들)}개를 만들었습니다 -> {out} (발송은 하지 않았습니다)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
