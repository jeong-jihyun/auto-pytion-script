"""SQLite 데이터베이스 파일을 안전하게 백업하고, 백업본이 멀쩡한지 검사하는 스크립트.

생각의 흐름:
  1) 사내 소규모 도구(재고·접수·로그 수집)는 SQLite 파일 하나에 데이터를 담는 경우가 많습니다.
  2) 프로그램이 쓰는 중에 파일을 그냥 복사하면, 반쯤 쓰인 상태가 복사되어 백업이 깨질 수 있습니다.
     → 파이썬 sqlite3 의 backup() 기능을 쓰면 DB가 일관된 시점의 사본을 만들어 줍니다.
  3) 백업이 끝나면 확인을 두 번 합니다.
     - PRAGMA integrity_check : 파일 구조가 깨지지 않았는지
     - 테이블별 행 수 비교    : 원본과 백업의 행 수가 같은지
  4) 원본은 읽기 전용(mode=ro)으로 열어서 실수로라도 바꾸지 않게 합니다.
  5) 백업 파일 이름에 날짜시간을 붙여 덮어쓰지 않습니다. 검사 결과는 CSV로도 남겨 점검 기록으로 씁니다.
"""
import argparse
import csv
import os
import sqlite3
import sys
from datetime import datetime


def table_counts(conn):
    names = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    # 테이블 이름에 큰따옴표가 있을 수 있으므로 두 번 써서 감쌉니다
    return {n: conn.execute('SELECT COUNT(*) FROM "%s"' % n.replace('"', '""')).fetchone()[0] for n in names}


def integrity(conn):
    rows = [r[0] for r in conn.execute("PRAGMA integrity_check")]
    return "ok" if rows == ["ok"] else "; ".join(rows[:5])


def main():
    ap = argparse.ArgumentParser(description="SQLite 안전 백업 + 무결성 검사")
    ap.add_argument("db", help="원본 SQLite 파일")
    ap.add_argument("--out-dir", default="backup_out", help="백업 파일을 둘 폴더 (기본 backup_out)")
    ap.add_argument("--check-only", action="store_true", help="백업하지 않고 원본 무결성·행 수만 확인")
    ap.add_argument("--report", default=None, help="검사 결과 CSV (기본: 백업 폴더/verify_날짜시간.csv)")
    args = ap.parse_args()

    if not os.path.isfile(args.db):
        sys.exit(f"[오류] 파일이 없습니다: {args.db}")
    src_uri = "file:" + os.path.abspath(args.db).replace("?", "%3f") + "?mode=ro"
    try:
        src = sqlite3.connect(src_uri, uri=True)
        src_ok = integrity(src)
        src_counts = table_counts(src)
    except sqlite3.DatabaseError as e:
        sys.exit(f"[오류] SQLite 파일로 열 수 없습니다: {e}")

    print(f"원본: {args.db}")
    print(f"  무결성 검사: {src_ok}")
    for t, n in src_counts.items():
        print(f"  {t}: {n}행")
    if args.check_only:
        src.close()
        sys.exit(0 if src_ok == "ok" else 1)

    os.makedirs(args.out_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = os.path.splitext(os.path.basename(args.db))[0]
    dst_path = os.path.join(args.out_dir, f"{base}_{stamp}.db")
    if os.path.exists(dst_path):
        sys.exit(f"[오류] 같은 이름의 백업이 이미 있습니다(덮어쓰지 않음): {dst_path}")

    dst = sqlite3.connect(dst_path)
    src.backup(dst)                          # 일관된 시점의 사본을 만듭니다
    dst.close()
    src.close()

    chk = sqlite3.connect("file:" + os.path.abspath(dst_path) + "?mode=ro", uri=True)
    dst_ok = integrity(chk)
    dst_counts = table_counts(chk)
    chk.close()

    rows, all_ok = [], dst_ok == "ok" and src_ok == "ok"
    for t in sorted(set(src_counts) | set(dst_counts)):
        a, b = src_counts.get(t), dst_counts.get(t)
        same = a == b
        all_ok = all_ok and same
        rows.append({"테이블": t, "원본행수": a, "백업행수": b, "일치": "예" if same else "아니오"})

    report = args.report or os.path.join(args.out_dir, f"verify_{stamp}.csv")
    with open(report, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["테이블", "원본행수", "백업행수", "일치"])
        w.writeheader()
        w.writerows(rows)
        f.write(f"\n# 원본 무결성,{src_ok}\n# 백업 무결성,{dst_ok}\n")

    size = os.path.getsize(dst_path)
    print(f"백업: {dst_path} ({size:,} bytes)")
    print(f"  무결성 검사: {dst_ok}")
    for r in rows:
        print(f"  {r['테이블']}: 원본 {r['원본행수']} / 백업 {r['백업행수']} → {r['일치']}")
    print(f"결과: {'정상' if all_ok else '확인 필요'} (기록: {report})")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
