"""CSV 파일을 INSERT 문이 든 .sql 파일로 바꾸는 스크립트(만들기만 하고 실행은 하지 않음).

생각의 흐름:
  1) 헤더(첫 줄)를 컬럼 이름으로 씁니다. 영문·숫자·밑줄만 허용해 이상한 이름을 막습니다.
  2) 값이 전부 숫자인 컬럼은 따옴표 없이, 아니면 작은따옴표로 감쌉니다. 따옴표는 두 개로 바꿔 이스케이프합니다.
  3) 빈 칸은 NULL 로 만듭니다.
  4) --batch 개수만큼 한 INSERT 에 묶습니다.
  5) 만들어진 .sql 은 사람이 검토한 뒤 DB 도구에서 직접 실행합니다.
"""
import argparse
import csv
import re
from pathlib import Path

NUM = re.compile(r"^-?\d+(\.\d+)?$")
IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def main():
    p = argparse.ArgumentParser(description="CSV -> INSERT SQL")
    p.add_argument("--input", required=True)
    p.add_argument("--table", required=True, help="테이블 이름")
    p.add_argument("--out", default="output/insert.sql")
    p.add_argument("--batch", type=int, default=100, help="한 INSERT 에 묶을 줄 수")
    a = p.parse_args()

    if not IDENT.match(a.table):
        raise SystemExit("테이블 이름은 영문·숫자·밑줄만 쓸 수 있습니다")
    with open(a.input, encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = [r for r in reader if any(c.strip() for c in r)]
    for h in header:
        if not IDENT.match(h):
            raise SystemExit(f"컬럼 이름 '{h}' 이(가) 안전하지 않습니다. 영문·숫자·밑줄로 바꿔 주세요")
    numeric = [all((not r[i].strip()) or NUM.match(r[i].strip()) for r in rows) for i in range(len(header))]

    def lit(i, v):
        v = v.strip()
        if v == "":
            return "NULL"
        return v if numeric[i] else "'" + v.replace("'", "''") + "'"

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    cols = ", ".join(header)
    with open(out, "w", encoding="utf-8") as f:
        f.write(f"-- {a.input} 에서 만든 파일입니다. 실행 전에 꼭 확인하세요.\n")
        for s in range(0, len(rows), a.batch):
            chunk = rows[s:s + a.batch]
            vals = ",\n".join("  (" + ", ".join(lit(i, v) for i, v in enumerate(r)) + ")" for r in chunk)
            f.write(f"INSERT INTO {a.table} ({cols}) VALUES\n{vals};\n")
    print(f"완료: {len(rows)}줄 -> {out}")


if __name__ == "__main__":
    main()
