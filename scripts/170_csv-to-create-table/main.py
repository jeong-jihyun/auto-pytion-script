"""CSV 내용을 훑어 열마다 알맞은 자료형을 추정하고, DB에 표를 만드는 CREATE TABLE 문을 만들어 주는 스크립트.

생각의 흐름:
  1) 엑셀·CSV로 받은 데이터를 DB에 올리려면 먼저 표(테이블)를 만들어야 하는데,
     열이 수십 개면 자료형과 길이를 하나하나 정하는 게 번거롭고 실수가 납니다.
  2) 그래서 열의 모든 값을 보고 '모두 정수면 INTEGER/BIGINT, 소수가 있으면 DECIMAL(전체자리, 소수자리),
     모두 날짜면 DATE, 날짜+시각이면 TIMESTAMP, 아니면 VARCHAR(가장 긴 길이에 여유)'로 추정합니다.
  3) 앞자리 0이 있는 코드(예: 00123, 우편번호, 계좌·사번)는 숫자로 바꾸면 0이 사라지므로 문자열로 둡니다.
  4) 빈칸이 하나도 없으면 NOT NULL, 값이 모두 다르고 이름이 ID·코드·번호로 끝나면 기본키 후보로 표시합니다.
  5) DB마다 문법이 조금 달라 --dialect 로 postgres / mysql / oracle / sqlite 를 고릅니다.
  6) 한글 열 이름은 DB에서 다루기 불편할 수 있어, --rename 으로 '한글=영문' 대응을 주면 바꿔 쓰고
     원래 이름은 주석(COMMENT)으로 남깁니다. 이 스크립트는 SQL 문만 만들고 DB에 실행하지는 않습니다.
"""
import argparse
import csv
import os
import re
from datetime import datetime

DATE_FMTS = ["%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y%m%d"]
TS_FMTS = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"]
INT_RE = re.compile(r"^-?\d+$")
DEC_RE = re.compile(r"^-?\d+\.\d+$")


def is_fmt(v, fmts):
    for f in fmts:
        try:
            datetime.strptime(v, f)
            return True
        except ValueError:
            pass
    return False


def infer(values):
    """빈칸을 뺀 값들 → (종류, 정보)."""
    vals = [v for v in values if v != ""]
    if not vals:
        return "text", {"len": 1}
    clean = [v.replace(",", "") for v in vals]
    if all(INT_RE.match(v) for v in clean) and not any(len(v) > 1 and v.lstrip("-").startswith("0") for v in clean):
        big = max(abs(int(v)) for v in clean)
        return ("bigint" if big > 2_147_483_647 else "int"), {}
    if all(INT_RE.match(v) or DEC_RE.match(v) for v in clean) and not any(
            INT_RE.match(v) and len(v) > 1 and v.lstrip("-").startswith("0") for v in clean):
        scale = max(len(v.split(".")[1]) if "." in v else 0 for v in clean)
        whole = max(len(v.lstrip("-").split(".")[0]) for v in clean)
        return "decimal", {"p": min(whole + scale + 2, 38), "s": scale}   # +2 자리 여유
    if all(is_fmt(v, DATE_FMTS) for v in vals) and not all(INT_RE.match(v) for v in vals):
        return "date", {}
    if all(is_fmt(v, TS_FMTS) for v in vals):
        return "timestamp", {}
    longest = max(len(v) for v in vals)
    return "text", {"len": longest}


def sql_type(kind, info, dialect, slack):
    if kind == "int":
        return {"oracle": "NUMBER(10)"}.get(dialect, "INTEGER")
    if kind == "bigint":
        return {"oracle": "NUMBER(19)", "sqlite": "INTEGER"}.get(dialect, "BIGINT")
    if kind == "decimal":
        return f"NUMBER({info['p']},{info['s']})" if dialect == "oracle" else (
            "REAL" if dialect == "sqlite" else f"DECIMAL({info['p']},{info['s']})")
    if kind == "date":
        return "TEXT" if dialect == "sqlite" else "DATE"
    if kind == "timestamp":
        return {"sqlite": "TEXT", "mysql": "DATETIME", "oracle": "TIMESTAMP"}.get(dialect, "TIMESTAMP")
    n = max(10, int(info["len"] * slack + 0.999))
    if dialect == "sqlite":
        return "TEXT"
    return f"VARCHAR2({n} CHAR)" if dialect == "oracle" else f"VARCHAR({n})"


def quote(name, dialect):
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        return name
    return f"`{name}`" if dialect == "mysql" else f'"{name}"'


def main():
    p = argparse.ArgumentParser(description="CSV → CREATE TABLE 문 만들기(실행은 안 함)")
    p.add_argument("input")
    p.add_argument("-t", "--table", help="표 이름(기본: 파일 이름)")
    p.add_argument("-d", "--dialect", choices=["postgres", "mysql", "oracle", "sqlite"], default="postgres")
    p.add_argument("--rename", help="열 이름 바꾸기 'a=b,c=d' 또는 그런 줄이 든 파일 경로")
    p.add_argument("--slack", type=float, default=1.5, help="문자열 길이 여유 배수(기본 1.5)")
    p.add_argument("-o", "--output", help="SQL 저장 경로(기본 out/<표이름>.sql)")
    p.add_argument("--encoding", default="utf-8-sig")
    a = p.parse_args()

    table = a.table or re.sub(r"\W", "_", os.path.splitext(os.path.basename(a.input))[0])
    rename = {}
    if a.rename:
        text = open(a.rename, encoding="utf-8-sig").read().replace("\n", ",") if os.path.exists(a.rename) else a.rename
        for pair in text.split(","):
            if "=" in pair:
                k, v = pair.split("=", 1)
                rename[k.strip()] = v.strip()

    with open(a.input, newline="", encoding=a.encoding) as f:
        reader = csv.reader(f)
        header = next(reader)
        cols = [[] for _ in header]
        nrows = 0
        for row in reader:
            nrows += 1
            for i in range(len(header)):
                cols[i].append(row[i].strip() if i < len(row) else "")

    lines, comments, report, pk = [], [], [], None
    for name, vals in zip(header, cols):
        kind, info = infer(vals)
        t = sql_type(kind, info, a.dialect, a.slack)
        new = rename.get(name, name)
        notnull = all(v != "" for v in vals)
        unique = len(set(vals)) == len(vals) and notnull
        if pk is None and unique and re.search(r"(id|코드|번호|no)$", name, re.I):
            pk = new
        lines.append(f"    {quote(new, a.dialect)} {t}{' NOT NULL' if notnull else ''}")
        if new != name:
            comments.append((new, name))
        blanks = sum(1 for v in vals if v == "")
        report.append(f"  {name:<10} → {new:<14} {t:<20} 빈칸 {blanks}, 고유값 {len(set(vals))}"
                      + ("  (앞자리 0 → 문자열 유지)" if kind == "text" and any(re.fullmatch(r"0\d+", v) for v in vals) else ""))
    if pk:
        lines.append(f"    PRIMARY KEY ({quote(pk, a.dialect)})")
    sql = [f"-- {os.path.basename(a.input)} ({nrows}행) 을 보고 추정한 표입니다. 실행 전에 자료형·길이를 꼭 확인하세요.",
           f"CREATE TABLE {quote(table, a.dialect)} (", ",\n".join(lines), ");"]
    for new, old in comments:
        old_esc = old.replace("'", "''")
        if a.dialect in ("postgres", "oracle"):
            sql.append(f"COMMENT ON COLUMN {quote(table, a.dialect)}.{quote(new, a.dialect)} IS '{old_esc}';")
        else:
            sql.append(f"-- {new}: 원래 열 이름 '{old}'")

    out = a.output or os.path.join("out", f"{table}.sql")
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(sql) + "\n")
    print(f"[{a.dialect}] {table}: 열 {len(header)}개, {nrows}행 확인 → {out}")
    print("\n".join(report))
    print(f"  기본키 후보: {pk or '없음'}")


if __name__ == "__main__":
    main()
