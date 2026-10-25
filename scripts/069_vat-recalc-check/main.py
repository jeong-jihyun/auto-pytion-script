"""세금계산서·청구 내역의 공급가액·세액·합계가 서로 맞는지 다시 계산해 검산하는 스크립트.

규칙: 세액 = 공급가액 × 세율(기본 10%, 원 미만 반올림), 합계 = 공급가액 + 세액.
원 단위 차이가 --tolerance(기본 0원)보다 크면 '불일치'로 알려 줍니다.
(실제 세무 처리는 세무 담당자 확인이 필요합니다. 이 도구는 단순 산식 검산용입니다.)
"""
import argparse
import csv
import sys
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from pathlib import Path


def num(s):
    return Decimal((s or "").replace(",", "").strip())


def main():
    p = argparse.ArgumentParser(description="공급가액·세액·합계 검산")
    p.add_argument("input", type=Path)
    p.add_argument("--supply-col", default="공급가액")
    p.add_argument("--vat-col", default="세액")
    p.add_argument("--total-col", default="합계")
    p.add_argument("--rate", type=Decimal, default=Decimal("0.10"), help="세율(0.10 = 10%)")
    p.add_argument("--tolerance", type=Decimal, default=Decimal(0), help="허용 차이(원)")
    p.add_argument("-o", "--output", type=Path, default=Path("output/vat_check.csv"))
    a = p.parse_args()

    with a.input.open(newline="", encoding="utf-8-sig") as fp:
        r = csv.DictReader(fp)
        fields = r.fieldnames or []
        for need in (a.supply_col, a.vat_col, a.total_col):
            if need not in fields:
                print(f"[오류] 없는 열: {need} (있는 열: {fields})")
                sys.exit(1)
        rows = list(r)

    out, bad = [], 0
    for ln, row in enumerate(rows, start=2):
        try:
            sup, vat, tot = num(row[a.supply_col]), num(row[a.vat_col]), num(row[a.total_col])
        except InvalidOperation:
            out.append({"줄": ln, **row, "계산세액": "", "계산합계": "", "판정": "숫자 오류"})
            bad += 1
            continue
        calc_vat = (sup * a.rate).quantize(Decimal("1"), ROUND_HALF_UP)
        calc_tot = sup + calc_vat
        problems = []
        if abs(vat - calc_vat) > a.tolerance:
            problems.append(f"세액 차이 {vat - calc_vat}")
        if abs(tot - (sup + vat)) > a.tolerance:
            problems.append(f"합계≠공급가액+세액 (차이 {tot - (sup + vat)})")
        bad += bool(problems)
        out.append({"줄": ln, **row, "계산세액": str(calc_vat), "계산합계": str(calc_tot),
                    "판정": "; ".join(problems) if problems else "일치"})

    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.DictWriter(fp, fieldnames=["줄"] + fields + ["계산세액", "계산합계", "판정"])
        w.writeheader()
        w.writerows(out)
    print(f"{len(out)}건 중 불일치 {bad}건 → {a.output}")


if __name__ == "__main__":
    main()
