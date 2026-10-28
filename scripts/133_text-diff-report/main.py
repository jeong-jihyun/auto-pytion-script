"""두 텍스트 파일(SQL·설정·배치 스크립트 등)의 바뀐 줄을 HTML 보고서와 요약으로 보여 주는 스크립트.

생각의 흐름:
  1) 운영 반영 전 '이전 버전과 무엇이 바뀌었나'를 검토자에게 보여 줘야 할 때가 많습니다.
     git이 없는 환경(메일로 받은 파일, 서버에서 내려받은 파일)에서도 바로 비교하고 싶습니다.
  2) 파이썬 기본 모듈 difflib 로 줄 단위 차이를 계산합니다.
  3) 결과를 두 가지로 냅니다.
       - HTML: 좌우 나란히 보기(바뀐 곳 색칠). 브라우저로 열어 결재·메일 첨부용
       - 화면: 추가/삭제/변경 줄 수 요약 + unified diff(--show)
  4) 공백만 바뀐 줄 때문에 검토가 방해되지 않게 --ignore-space 옵션으로 줄 끝 공백·연속 공백을 무시할 수 있게 합니다.
  5) 인코딩이 cp949인 옛 파일도 있어서 utf-8로 못 읽으면 cp949로 다시 읽습니다.
"""
import argparse
import difflib
import re
from pathlib import Path


def read_lines(path):
    for enc in ("utf-8-sig", "cp949"):
        try:
            return path.read_text(encoding=enc).splitlines()
        except UnicodeDecodeError:
            continue
    raise SystemExit(f"[오류] 글자 인코딩을 알 수 없습니다: {path}")


def squash(line):
    return re.sub(r"\s+", " ", line).strip()


def main():
    p = argparse.ArgumentParser(description="두 텍스트 파일 비교 보고서")
    p.add_argument("old", type=Path, help="이전 파일")
    p.add_argument("new", type=Path, help="새 파일")
    p.add_argument("--ignore-space", action="store_true", help="공백 차이 무시")
    p.add_argument("--context", type=int, default=3, help="바뀐 곳 앞뒤로 보여 줄 줄 수(기본 3)")
    p.add_argument("--show", action="store_true", help="화면에 unified diff 도 출력")
    p.add_argument("-o", "--output", type=Path, default=Path("output/diff_report.html"))
    a = p.parse_args()

    old, new = read_lines(a.old), read_lines(a.new)
    cmp_old = [squash(x) for x in old] if a.ignore_space else old
    cmp_new = [squash(x) for x in new] if a.ignore_space else new

    # 몇 줄이 추가·삭제·변경됐는지 셉니다
    added = deleted = changed = 0
    sm = difflib.SequenceMatcher(None, cmp_old, cmp_new, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "insert":
            added += j2 - j1
        elif tag == "delete":
            deleted += i2 - i1
        elif tag == "replace":
            n = min(i2 - i1, j2 - j1)
            changed += n
            added += (j2 - j1) - n
            deleted += (i2 - i1) - n

    if added == deleted == changed == 0:
        print("두 파일의 내용이 같습니다" + (" (공백 차이 무시)" if a.ignore_space else ""))
    else:
        print(f"추가 {added}줄, 삭제 {deleted}줄, 변경 {changed}줄 (이전 {len(old)}줄 → 새 {len(new)}줄)")

    if a.show:
        for line in difflib.unified_diff(cmp_old, cmp_new, str(a.old), str(a.new), n=a.context, lineterm=""):
            print(line)

    html = difflib.HtmlDiff(wrapcolumn=80).make_file(
        cmp_old, cmp_new, f"이전: {a.old.name}", f"새: {a.new.name}", context=True, numlines=a.context)
    html = html.replace('<meta http-equiv="Content-Type"\n          content="text/html; charset=utf-8" />',
                        '<meta charset="utf-8" />')
    summary = (f'<p style="font-family:sans-serif">추가 {added}줄 · 삭제 {deleted}줄 · 변경 {changed}줄'
               f'{" (공백 차이 무시)" if a.ignore_space else ""}</p>')
    html = html.replace("<title></title>", "<title>파일 비교 보고서</title>", 1)
    html = html.replace("<body>", "<body>\n" + summary, 1)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(html, encoding="utf-8")
    print(f"저장: {a.output}")


if __name__ == "__main__":
    main()
