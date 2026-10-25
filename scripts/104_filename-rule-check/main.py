"""폴더 안 파일 이름이 회사·팀의 '파일 이름 규칙'을 지키는지 점검하는 스크립트.

생각의 흐름:
  1) 규칙은 정규식으로 받습니다. 기본 규칙 예: 문서번호_YYYYMMDD_제목_v버전.확장자
     예) ABC-001_20261025_주간보고_v1.docx
  2) 정규식에 맞지 않으면 '규칙 위반'. 맞더라도 날짜 부분이 실제 없는 날짜(20261345)면 '날짜 오류'.
  3) 같은 문서번호·제목에 버전이 여러 개면 가장 높은 버전 하나만 '최신'으로 표시해, 옛 버전 정리를 돕습니다.
  4) 공백·특수문자(\\ / : * ? " < > |)처럼 다른 PC·클라우드에서 문제를 일으키는 글자도 경고합니다.
  파일은 읽기만 하고 이름을 바꾸지 않습니다(이름 바꾸기는 003 스크립트).
"""
import argparse
import csv
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

DEFAULT_RULE = r"^(?P<docno>[A-Z]{2,5}-\d{3})_(?P<date>\d{8})_(?P<title>[^_]+)_v(?P<ver>\d+)\.(?P<ext>[A-Za-z0-9]+)$"
BAD_CHARS = re.compile(r'[\\/:*?"<>|]|\s')


def main():
    p = argparse.ArgumentParser(description="파일 이름 규칙 점검")
    p.add_argument("folder", type=Path)
    p.add_argument("--rule", default=DEFAULT_RULE, help="정규식(이름 그룹 date, ver, docno, title 있으면 추가 점검)")
    p.add_argument("--recursive", action="store_true", help="하위 폴더까지")
    p.add_argument("-o", "--output", type=Path, default=Path("output/filename_check.csv"))
    a = p.parse_args()

    rx = re.compile(a.rule)
    files = sorted(a.folder.rglob("*") if a.recursive else a.folder.iterdir())
    files = [f for f in files if f.is_file()]
    rows, versions = [], defaultdict(list)
    for f in files:
        name = f.name
        probs = []
        m = rx.match(name)
        if not m:
            probs.append("규칙 위반")
        else:
            gd = m.groupdict()
            if gd.get("date"):
                try:
                    datetime.strptime(gd["date"], "%Y%m%d")
                except ValueError:
                    probs.append(f"날짜 오류({gd['date']})")
            if gd.get("ver") and gd.get("docno") is not None:
                versions[(gd.get("docno"), gd.get("title"))].append((int(gd["ver"]), len(rows)))
        if BAD_CHARS.search(name):
            probs.append("공백·특수문자 포함")
        rows.append([str(f.relative_to(a.folder)), "정상" if not probs else "확인 필요", " / ".join(probs), ""])
    for key, vs in versions.items():
        if len(vs) > 1:
            top = max(v for v, _ in vs)
            for v, idx in vs:
                rows[idx][3] = "최신" if v == top else f"옛 버전(최신 v{top})"
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["파일", "결과", "문제", "버전"])
        w.writerows(rows)
    bad = sum(1 for r in rows if r[1] != "정상")
    old = sum(1 for r in rows if r[3].startswith("옛"))
    print(f"파일 {len(rows)}개 중 규칙 확인 필요 {bad}개, 옛 버전 {old}개 → {a.output}")
    for r in rows:
        if r[1] != "정상" or r[3].startswith("옛"):
            print(f"  - {r[0]}: " + " / ".join(x for x in (r[2], r[3]) if x))


if __name__ == "__main__":
    main()
