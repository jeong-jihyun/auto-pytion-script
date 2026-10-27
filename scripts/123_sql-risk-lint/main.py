"""운영 DB에 반영할 SQL 파일에서 위험한 문장을 미리 찾아 주는 스크립트.

생각의 흐름:
  1) 운영 반영 사고의 단골은 'WHERE 없는 UPDATE/DELETE', 실수로 넣은 DROP/TRUNCATE 입니다.
  2) SQL 파일을 읽어 주석(-- , /* */)과 따옴표 안 글자를 먼저 지웁니다.
     그래야 주석이나 문자열 속 'DELETE' 같은 글자에 속지 않습니다. (줄 번호는 그대로 유지)
  3) 세미콜론(;)으로 문장을 나누고, 문장마다 규칙을 검사합니다.
       위험: WHERE 없는 UPDATE/DELETE, WHERE 1=1, DROP, TRUNCATE, ALTER ... DROP
       주의: 열 이름 없는 INSERT, GRANT/REVOKE
       참고: SELECT *
  4) 결과를 화면과 CSV로 남기고, '위험'이 하나라도 있으면 종료 코드 1 (반영 전 자동 점검에 쓰기 좋게).
  ※ 이 스크립트는 SQL을 실행하지 않습니다. 글자만 읽습니다.
"""
import argparse
import csv
import re
import sys
from pathlib import Path


def blank_out(sql):
    """주석과 문자열을 공백으로 바꿉니다(줄바꿈은 남겨서 줄 번호를 지킴)."""
    out, i, n = [], 0, len(sql)
    while i < n:
        c, nxt = sql[i], sql[i + 1] if i + 1 < n else ""
        if c == "-" and nxt == "-":  # 한 줄 주석
            j = sql.find("\n", i)
            j = n if j == -1 else j
            out.append(" " * (j - i))
            i = j
        elif c == "/" and nxt == "*":  # 여러 줄 주석
            j = sql.find("*/", i + 2)
            j = n if j == -1 else j + 2
            out.append(re.sub(r"[^\n]", " ", sql[i:j]))
            i = j
        elif c == "'":  # 문자열 '...' ('' 는 따옴표 하나)
            j = i + 1
            while j < n:
                if sql[j] == "'" and j + 1 < n and sql[j + 1] == "'":
                    j += 2
                    continue
                if sql[j] == "'":
                    break
                j += 1
            out.append("'" + re.sub(r"[^\n]", " ", sql[i + 1:j]) + "'")
            i = j + 1
        else:
            out.append(c)
            i += 1
    return "".join(out)


RULES = [
    ("위험", "DROP 문", re.compile(r"^\s*DROP\s", re.I)),
    ("위험", "TRUNCATE 문", re.compile(r"^\s*TRUNCATE\s", re.I)),
    ("위험", "ALTER ... DROP (열·제약 삭제)", re.compile(r"^\s*ALTER\s.*\sDROP\s", re.I | re.S)),
    ("주의", "GRANT/REVOKE 권한 변경", re.compile(r"^\s*(GRANT|REVOKE)\s", re.I)),
    ("참고", "SELECT * (필요한 열만 고르기 권장)", re.compile(r"\bSELECT\s+\*", re.I)),
]


def check_statement(stmt):
    found = []
    head = stmt.lstrip().upper()
    if re.match(r"(UPDATE|DELETE)\b", head):
        if not re.search(r"\bWHERE\b", stmt, re.I):
            found.append(("위험", "WHERE 없는 " + head.split()[0] + " (전체 행이 바뀜)"))
        elif re.search(r"\bWHERE\s+(1\s*=\s*1|'(\s*)'\s*=\s*'(\s*)')\s*($|;)", stmt.strip(), re.I):
            found.append(("위험", "WHERE 1=1 뿐인 " + head.split()[0]))
    if re.match(r"INSERT\s+INTO\s+[\w.\"`\[\]]+\s+(VALUES|SELECT)\b", head):
        found.append(("주의", "열 이름 없는 INSERT (테이블 구조가 바뀌면 깨짐)"))
    for level, name, pat in RULES:
        if pat.search(stmt):
            found.append((level, name))
    return found


def main():
    p = argparse.ArgumentParser(description="SQL 반영 전 위험 구문 점검(실행 안 함)")
    p.add_argument("paths", nargs="+", type=Path, help="SQL 파일 또는 폴더(폴더면 *.sql 전부)")
    p.add_argument("--encoding", default="utf-8", help="파일 인코딩(기본 utf-8, 예: cp949)")
    p.add_argument("-o", "--output", type=Path, default=Path("output/sql_lint.csv"))
    a = p.parse_args()

    files = []
    for path in a.paths:
        files += sorted(path.rglob("*.sql")) if path.is_dir() else [path]

    results = []
    for f in files:
        raw = f.read_text(encoding=a.encoding)
        clean = blank_out(raw)
        raw_lines = raw.splitlines()
        pos, no = 0, 0
        for part in clean.split(";"):
            start = pos
            pos += len(part) + 1
            if not part.strip():
                continue
            no += 1
            lead = len(part) - len(part.lstrip())
            line = clean.count("\n", 0, start + lead) + 1
            preview = raw_lines[line - 1].strip()[:80] if line - 1 < len(raw_lines) else ""
            for level, rule in check_statement(part):
                results.append([str(f), no, line, level, rule, preview])

    order = {"위험": 0, "주의": 1, "참고": 2}
    results.sort(key=lambda r: (order[r[3]], r[0], r[2]))
    for r in results:
        print(f"[{r[3]}] {Path(r[0]).name}:{r[2]} (문장 {r[1]}) {r[4]}\n        {r[5]}")
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["파일", "문장번호", "줄", "등급", "규칙", "첫줄"])
        w.writerows(results)
    cnt = {k: sum(1 for r in results if r[3] == k) for k in order}
    print(f"\n파일 {len(files)}개 | 위험 {cnt['위험']} · 주의 {cnt['주의']} · 참고 {cnt['참고']} -> {a.output}")
    sys.exit(1 if cnt["위험"] else 0)


if __name__ == "__main__":
    main()
