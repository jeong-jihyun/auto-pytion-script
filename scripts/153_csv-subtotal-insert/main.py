"""CSV를 그룹 열 기준으로 정렬하고, 그룹이 바뀔 때마다 '소계' 행을, 맨 끝에 '총계' 행을 끼워 넣는 스크립트.

생각의 흐름:
  1) 엑셀의 '부분합' 기능을 매번 손으로 누르는 일을 대신합니다. 결과는 사람이 바로 읽는 보고용 표입니다.
  2) 그룹 열은 여러 개 줄 수 있습니다(예: 부서,팀). 바깥 그룹이 바뀌면 안쪽 소계 → 바깥 소계 순서로 넣습니다.
  3) 합계를 낼 숫자 열은 --sum 으로 지정합니다. '1,200' 같은 쉼표 숫자도 읽습니다.
  4) 원본 순서를 지키고 싶으면 --no-sort 를 씁니다(이미 정렬된 파일일 때).
  5) 소계 행에는 건수도 같이 적어 줍니다.
"""
import argparse
import csv
from decimal import Decimal, InvalidOperation


def num(s):
    try:
        return Decimal(str(s).replace(",", "").strip() or "0")
    except InvalidOperation:
        return Decimal(0)


def fmt(d):
    d = d.normalize()
    return f"{d:f}" if d != d.to_integral() else f"{d.to_integral():f}"


def main():
    p = argparse.ArgumentParser(description="CSV 소계·총계 행 삽입(엑셀 부분합)")
    p.add_argument("input")
    p.add_argument("--group", required=True, help="그룹 열(쉼표로 여러 개, 바깥→안쪽 순)")
    p.add_argument("--sum", required=True, help="합계 낼 숫자 열(쉼표 구분)")
    p.add_argument("--no-sort", action="store_true", help="정렬하지 않고 원본 순서 그대로")
    p.add_argument("--label", default="소계", help="소계 표시 글자")
    p.add_argument("-o", "--output", default="subtotal.out.csv")
    a = p.parse_args()

    with open(a.input, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames
        rows = list(reader)
    groups = [g.strip() for g in a.group.split(",")]
    sums = [s.strip() for s in a.sum.split(",")]
    for c in groups + sums:
        if c not in cols:
            raise SystemExit(f"[오류] 열 '{c}' 이 없습니다. 있는 열: {cols}")
    if not a.no_sort:
        rows.sort(key=lambda r: tuple(r[g] for g in groups))
    out_cols = cols + ["건수"] if "건수" not in cols else cols

    def blank_acc():
        return {"n": 0, **{s: Decimal(0) for s in sums}}

    def subtotal_row(level, key, acc):
        r = {c: "" for c in out_cols}
        for i in range(level + 1):
            r[groups[i]] = key[i]
        r[groups[level]] = f"{key[level]} {a.label}"
        for s in sums:
            r[s] = fmt(acc[s])
        r["건수"] = acc["n"]
        return r

    out = []
    accs = [blank_acc() for _ in groups]
    total = blank_acc()
    prev = None
    n_sub = 0
    for r in rows:
        key = tuple(r[g] for g in groups)
        if prev is not None:
            # 바뀐 가장 바깥 레벨을 찾고, 안쪽부터 소계를 닫습니다
            changed = next((i for i in range(len(groups)) if key[i] != prev[i]), None)
            if changed is not None:
                for lv in range(len(groups) - 1, changed - 1, -1):
                    out.append(subtotal_row(lv, prev, accs[lv]))
                    accs[lv] = blank_acc()
                    n_sub += 1
        out.append({**r, "건수": r.get("건수", "")})
        for acc in accs + [total]:
            acc["n"] += 1
            for s in sums:
                acc[s] += num(r[s])
        prev = key
    if prev is not None:
        for lv in range(len(groups) - 1, -1, -1):
            out.append(subtotal_row(lv, prev, accs[lv]))
            n_sub += 1
    tr = {c: "" for c in out_cols}
    tr[groups[0]] = "총계"
    for s in sums:
        tr[s] = fmt(total[s])
    tr["건수"] = total["n"]
    out.append(tr)

    with open(a.output, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=out_cols)
        w.writeheader()
        w.writerows(out)
    print(f"원본 {len(rows)}행 + 소계 {n_sub}행 + 총계 1행 → {a.output}")
    print("총계: " + ", ".join(f"{s}={fmt(total[s])}" for s in sums))


if __name__ == "__main__":
    main()
