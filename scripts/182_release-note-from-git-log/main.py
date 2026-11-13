"""git log 출력 파일을 읽어 커밋을 종류별(기능·버그 수정·문서 등)로 묶은 릴리스 노트(마크다운)를 만드는 스크립트.

생각의 흐름:
  1) 배포할 때마다 '이번에 뭐가 바뀌었나'를 손으로 정리하면 빠뜨리기 쉽습니다.
  2) git 이 없는 PC에서도 쓸 수 있게, 저장소에서 아래 명령으로 뽑은 텍스트 파일을 입력으로 받습니다.
       git log --pretty=format:"%h|%ad|%an|%s" --date=short v1.2.0..HEAD > gitlog.txt
  3) 커밋 제목 앞머리로 종류를 나눕니다.
     - 영어 관례(Conventional Commits): feat:, fix:, docs:, refactor:, perf:, test:, chore:, build:, ci:
     - 한국어 말머리: [기능]/[추가] → 기능, [버그]/[수정] → 버그 수정, [문서] → 문서 ...
     - 둘 다 아니면 '기타'로 둡니다(억지로 짐작하지 않음).
  4) 'feat!:' 처럼 느낌표가 있거나 제목에 BREAKING 이 있으면 '호환성 깨짐'에 따로 한 번 더 적어 눈에 띄게 합니다.
  5) Merge 커밋은 내용이 겹치므로 기본으로 뺍니다(--keep-merge 로 포함 가능).
"""
import argparse
import os
import re
import sys
from collections import OrderedDict

# (분류 이름, 영어 접두어들, 한국어 말머리들) - 위에서부터 순서대로 출력합니다
CATEGORIES = [
    ("새 기능", ["feat"], ["기능", "추가", "신규"]),
    ("버그 수정", ["fix", "hotfix"], ["버그", "수정", "긴급"]),
    ("성능 개선", ["perf"], ["성능"]),
    ("구조 개선", ["refactor"], ["리팩터", "리팩토링", "개선"]),
    ("문서", ["docs"], ["문서"]),
    ("테스트", ["test"], ["테스트"]),
    ("빌드·배포·기타 작업", ["build", "ci", "chore"], ["빌드", "배포", "설정"]),
]
EN_RE = re.compile(r"^(?P<type>[a-zA-Z]+)(?:\((?P<scope>[^)]*)\))?(?P<bang>!)?:\s*(?P<msg>.+)$")
KO_RE = re.compile(r"^\[(?P<tag>[^\]]+)\]\s*(?P<msg>.+)$")


def classify(subject):
    """제목을 보고 (분류, 깔끔한 메시지, 범위, 호환성깨짐여부) 를 돌려줍니다."""
    breaking = "BREAKING" in subject.upper()
    m = EN_RE.match(subject)
    if m:
        t = m.group("type").lower()
        breaking = breaking or bool(m.group("bang"))
        for name, en, _ in CATEGORIES:
            if t in en:
                return name, m.group("msg"), m.group("scope") or "", breaking
    m = KO_RE.match(subject)
    if m:
        tag = m.group("tag").strip()
        for name, _, ko in CATEGORIES:
            if any(k in tag for k in ko):
                return name, m.group("msg"), "", breaking
    return "기타", subject, "", breaking


def read_log(path):
    commits, bad = [], []
    with open(path, encoding="utf-8-sig") as f:
        for no, line in enumerate(f, start=1):
            line = line.rstrip("\n")
            if not line.strip():
                continue
            parts = line.split("|", 3)
            if len(parts) != 4:
                bad.append(no)
                continue
            h, date, author, subject = (p.strip() for p in parts)
            commits.append({"hash": h, "date": date, "author": author, "subject": subject})
    return commits, bad


def main():
    ap = argparse.ArgumentParser(description="git log 텍스트로 릴리스 노트 만들기")
    ap.add_argument("logfile", help='git log --pretty=format:"%%h|%%ad|%%an|%%s" --date=short 결과 파일')
    ap.add_argument("--version", default="다음 버전", help="릴리스 노트 제목에 넣을 버전 이름")
    ap.add_argument("--since", help="이 날짜(YYYY-MM-DD) 이후 커밋만")
    ap.add_argument("--until", help="이 날짜(YYYY-MM-DD) 까지 커밋만")
    ap.add_argument("--keep-merge", action="store_true", help="Merge 커밋도 넣기")
    ap.add_argument("--with-author", action="store_true", help="각 줄에 작성자 이름 붙이기")
    ap.add_argument("--output", default="output/RELEASE_NOTES.md", help="결과 마크다운 파일")
    args = ap.parse_args()

    commits, bad = read_log(args.logfile)
    if not commits:
        sys.exit("[오류] 읽은 커밋이 없습니다. git log 형식(해시|날짜|작성자|제목)을 확인하세요.")

    groups = OrderedDict((name, []) for name, _, _ in CATEGORIES)
    groups["기타"] = []
    breaking, skipped_merge, used = [], 0, []
    for c in commits:
        if args.since and c["date"] < args.since:
            continue
        if args.until and c["date"] > args.until:
            continue
        if c["subject"].startswith("Merge ") and not args.keep_merge:
            skipped_merge += 1
            continue
        name, msg, scope, brk = classify(c["subject"])
        line = f"- {('**' + scope + '**: ') if scope else ''}{msg} (`{c['hash']}`"
        line += f", {c['author']})" if args.with_author else ")"
        groups[name].append(line)
        if brk:
            breaking.append(line)
        used.append(c)

    if not used:
        sys.exit("[알림] 조건에 맞는 커밋이 없습니다.")
    dates = sorted(c["date"] for c in used)
    out = [f"# 릴리스 노트 - {args.version}", "",
           f"기간: {dates[0]} ~ {dates[-1]} · 커밋 {len(used)}개", ""]
    if breaking:
        out += ["## ⚠ 호환성 깨짐 (꼭 확인)", *breaking, ""]
    for name, lines in groups.items():
        if lines:
            out += [f"## {name} ({len(lines)})", *lines, ""]

    d = os.path.dirname(args.output)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write("\n".join(out))

    print("\n".join(out))
    print("-" * 40)
    print(f"저장: {args.output}")
    print(f"분류별: " + ", ".join(f"{k} {len(v)}" for k, v in groups.items() if v))
    if skipped_merge:
        print(f"뺀 Merge 커밋: {skipped_merge}개")
    if bad:
        print(f"[주의] 형식이 맞지 않아 건너뛴 줄: {bad}")


if __name__ == "__main__":
    main()
