"""CSV를 임시 SQLite 데이터베이스에 넣고 SQL(SELECT)로 조회하는 스크립트.

파일 이름(확장자 뺀 것)이 그대로 테이블 이름이 됩니다. 여러 CSV를 넣고 JOIN 도 할 수 있습니다.
안전을 위해 SELECT 로 시작하는 문장만 실행하고, 데이터베이스는 메모리에만 만들어 쓰고 버립니다.
모든 열은 글자로 들어가므로 숫자 계산은 CAST(열 AS REAL) 를 쓰세요.
"""
import argparse
import csv
import re
import sqlite3
import sys
from pathlib import Path


def table_name(path: Path):
    """파일 이름을 안전한 테이블 이름으로 바꿉니다(영문·숫자·_ 만)."""
    name = re.sub(r"\W", "_", path.stem)
    return name if not name[0].isdigit() else "t_" + name


def load_csv(conn, path: Path):
    """CSV 한 개를 테이블로 넣고 (테이블이름, 행수) 를 돌려줍니다."""
    with path.open(newline="", encoding="utf-8-sig") as fp:
        r = csv.reader(fp)
        header = next(r)
        cols = ", ".join(f'"{h}"' for h in header)
        t = table_name(path)
        conn.execute(f'CREATE TABLE "{t}" ({cols})')
        marks = ",".join("?" * len(header))
        rows = [row for row in r if len(row) == len(header)]
        conn.executemany(f'INSERT INTO "{t}" VALUES ({marks})', rows)
    return t, len(rows)


def main():
    p = argparse.ArgumentParser(description="CSV를 SQL로 조회")
    p.add_argument("csv_files", nargs="+", type=Path, help="CSV 파일(여러 개 가능)")
    p.add_argument("-q", "--query", required=True, help="실행할 SELECT 문")
    p.add_argument("-o", "--output", type=Path, help="결과를 CSV로 저장(없으면 화면에 출력)")
    a = p.parse_args()

    if not a.query.lstrip().lower().startswith("select"):
        print("[오류] 안전을 위해 SELECT 문만 실행할 수 있습니다.")
        sys.exit(1)
    conn = sqlite3.connect(":memory:")
    for f in a.csv_files:
        t, n = load_csv(conn, f)
        print(f"테이블 '{t}' 에 {n}행을 넣었습니다")
    try:
        cur = conn.execute(a.query)
    except sqlite3.Error as e:
        print("[SQL 오류]", e)
        sys.exit(1)
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    if a.output:
        a.output.parent.mkdir(parents=True, exist_ok=True)
        with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
            w = csv.writer(fp)
            w.writerow(cols)
            w.writerows(rows)
        print(f"결과 {len(rows)}행 저장: {a.output}")
    else:
        print(" | ".join(cols))
        for row in rows:
            print(" | ".join(str(x) for x in row))
        print(f"({len(rows)}행)")


if __name__ == "__main__":
    main()
