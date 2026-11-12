"""가로로 펼쳐진 표(예: 지점 | 1월 | 2월 | 3월)를 세로로 긴 표(지점 | 월 | 값)로 바꾸는 스크립트(언피벗).

생각의 흐름:
  1) 엑셀 보고서는 사람이 보기 좋게 월·항목을 '열'로 펼쳐 둡니다.
     그런데 DB에 올리거나 피벗·그래프를 다시 만들려면 '한 줄에 값 하나'인 긴 모양이 필요합니다.
  2) 그대로 둘 열(--id, 예: 지점,담당)은 매 줄에 복사하고,
     나머지 열(또는 --cols 로 고른 열)은 '열 이름 → 항목 칸', '칸의 값 → 값 칸'으로 한 줄씩 풉니다.
  3) 빈칸은 기본으로 버립니다(--keep-empty 로 남길 수 있음).
     '1,200' 같은 쉼표 숫자는 --number 를 주면 쉼표를 지운 숫자로 바꿉니다.
  4) 051번(피벗)의 반대 방향입니다.
"""
import argparse
import csv
import os


def main():
    ap = argparse.ArgumentParser(description="가로 표 → 세로 표 (언피벗)")
    ap.add_argument("input", help="입력 CSV")
    ap.add_argument("--id", required=True, help="그대로 둘 열, 쉼표로 구분 (예: 지점,담당)")
    ap.add_argument("--cols", default="", help="풀 열(비우면 id 아닌 모든 열)")
    ap.add_argument("--var-name", default="항목", help="열 이름이 들어갈 새 열 이름 (기본: 항목)")
    ap.add_argument("--value-name", default="값", help="값이 들어갈 새 열 이름 (기본: 값)")
    ap.add_argument("--keep-empty", action="store_true", help="빈칸도 줄로 남깁니다")
    ap.add_argument("--number", action="store_true", help="값의 쉼표를 지워 숫자로 씁니다")
    ap.add_argument("-o", "--out", default="", help="출력 CSV (기본: out/<입력이름>_long.csv)")
    args = ap.parse_args()

    with open(args.input, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames
        rows = list(reader)

    ids = [c.strip() for c in args.id.split(",") if c.strip()]
    missing = [c for c in ids if c not in header]
    if missing:
        raise SystemExit(f"--id 열을 찾지 못했습니다: {missing}. 있는 열: {header}")
    cols = [c.strip() for c in args.cols.split(",") if c.strip()] or [c for c in header if c not in ids]
    missing = [c for c in cols if c not in header]
    if missing:
        raise SystemExit(f"--cols 열을 찾지 못했습니다: {missing}")

    out = args.out or os.path.join("out", os.path.splitext(os.path.basename(args.input))[0] + "_long.csv")
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    written = dropped = bad = 0
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(ids + [args.var_name, args.value_name])
        for r in rows:
            for c in cols:
                v = (r.get(c) or "").strip()
                if v == "" and not args.keep_empty:
                    dropped += 1
                    continue
                if args.number and v:
                    n = v.replace(",", "")
                    try:
                        float(n)
                        v = n
                    except ValueError:
                        bad += 1   # 숫자가 아니면 원래 글자 그대로 둡니다
                w.writerow([r[i] for i in ids] + [c, v])
                written += 1

    print(f"입력 {len(rows)}행 × 풀 열 {len(cols)}개 → 출력 {written}행 (빈칸 {dropped}개 버림)")
    print(f"  그대로 둔 열: {', '.join(ids)}")
    print(f"  푼 열: {', '.join(cols)}")
    if bad:
        print(f"  [확인] 숫자가 아닌 값 {bad}개는 글자 그대로 두었습니다")
    print(f"결과 → {out}")


if __name__ == "__main__":
    main()
