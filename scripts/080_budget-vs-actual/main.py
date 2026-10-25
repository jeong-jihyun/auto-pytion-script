"""예산 대비 실적(집행)을 부서·계정별로 비교해 집행률과 초과 여부를 보여 주는 스크립트.

생각의 흐름:
  1) 예산 CSV(부서, 계정, 예산)를 읽어 (부서, 계정) 별 예산을 만듭니다.
  2) 실적 CSV(일자, 부서, 계정, 금액)를 같은 키로 더합니다. --until 이 있으면 그 날짜까지만.
  3) 차이 = 예산 - 실적, 집행률 = 실적 / 예산 × 100 을 계산합니다.
  4) 집행률이 100% 넘으면 '초과', --warn(기본 90%) 넘으면 '주의',
     예산 없이 쓴 돈은 '예산 없음'으로 표시합니다.
  5) 부서별 소계와 전체 합계 줄을 붙입니다.
"""
import argparse
import csv
from collections import defaultdict
from decimal import Decimal
from pathlib import Path


def money(x):
    x = (x or "").replace(",", "").strip()
    return Decimal(x) if x else Decimal(0)


def judge(budget, actual, warn):
    if budget == 0:
        return "예산 없음" if actual else ""
    rate = actual / budget * 100
    if rate > 100:
        return "초과"
    if rate >= warn:
        return "주의"
    return "정상"


def line(dept, acct, b, act, warn):
    rate = f"{(act / b * 100):.1f}" if b else ""
    return {"부서": dept, "계정": acct, "예산": str(b), "실적": str(act), "잔액": str(b - act),
            "집행률(%)": rate, "판정": judge(b, act, warn)}


def main():
    p = argparse.ArgumentParser(description="예산 대비 실적 비교")
    p.add_argument("budget", type=Path, help="예산 CSV(부서,계정,예산)")
    p.add_argument("actual", type=Path, help="실적 CSV(일자,부서,계정,금액)")
    p.add_argument("--until", help="이 날짜(YYYY-MM-DD)까지의 실적만")
    p.add_argument("--warn", type=float, default=90, help="주의 표시 집행률(%)")
    p.add_argument("-o", "--output", type=Path, default=Path("output/budget_vs_actual.csv"))
    a = p.parse_args()

    bud, act = defaultdict(Decimal), defaultdict(Decimal)
    with a.budget.open(newline="", encoding="utf-8-sig") as fp:
        for r in csv.DictReader(fp):
            bud[(r["부서"].strip(), r["계정"].strip())] += money(r["예산"])
    with a.actual.open(newline="", encoding="utf-8-sig") as fp:
        for r in csv.DictReader(fp):
            if a.until and r["일자"] > a.until:
                continue  # 날짜가 YYYY-MM-DD 형식이면 글자 비교로 충분합니다
            act[(r["부서"].strip(), r["계정"].strip())] += money(r["금액"])

    out, alerts = [], 0
    depts = sorted({k[0] for k in bud} | {k[0] for k in act})
    tb = ta = Decimal(0)
    for dept in depts:
        keys = sorted(k for k in set(bud) | set(act) if k[0] == dept)
        sb = sa = Decimal(0)
        for k in keys:
            row = line(dept, k[1], bud[k], act[k], a.warn)
            alerts += row["판정"] in ("초과", "주의", "예산 없음")
            out.append(row)
            sb += bud[k]
            sa += act[k]
        out.append(line(dept, "[소계]", sb, sa, a.warn))
        tb += sb
        ta += sa
    out.append(line("[전체]", "[합계]", tb, ta, a.warn))

    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.DictWriter(fp, fieldnames=["부서", "계정", "예산", "실적", "잔액", "집행률(%)", "판정"])
        w.writeheader()
        w.writerows(out)
    print(f"계정 {len(out) - len(depts) - 1}줄, 확인 필요 {alerts}건 · 전체 집행률 {(ta / tb * 100 if tb else 0):.1f}% → {a.output}")


if __name__ == "__main__":
    main()
