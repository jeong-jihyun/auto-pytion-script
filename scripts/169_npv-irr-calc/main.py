"""투자안의 연도별 현금흐름으로 NPV(순현재가치)·IRR(내부수익률)·회수기간을 계산하고 여러 안을 비교하는 스크립트.

생각의 흐름:
  1) 시스템 도입·설비 투자 품의서에 'NPV, IRR, 회수기간'을 적어야 할 때가 많습니다. 엑셀 함수로 해도 되지만,
     안이 여러 개면 매번 표를 만들기 번거로워 CSV 한 장으로 비교하게 합니다.
  2) 입력은 '안,기간,현금흐름' 세로 형식입니다. 기간 0은 처음 투자(보통 음수)입니다.
  3) NPV = Σ 현금흐름_t ÷ (1+할인율)^t  (엑셀 NPV 함수와 달리 0기를 할인하지 않습니다 → 엑셀에서는 =NPV(r, 1기~)+0기)
  4) IRR은 NPV를 0으로 만드는 할인율입니다. 공식이 없어 '이분법'으로 찾습니다:
     -99%~1000% 를 촘촘히 훑어 NPV 부호가 바뀌는 칸을 찾고, 그 칸 안에서 반씩 줄여 가며 찾습니다.
     느리지만 항상 수렴하고 이해하기 쉽습니다.
     현금흐름 부호가 여러 번 바뀌면 IRR이 여러 개 나올 수 있어, 그때는 IRR 칸을 비우고 비고에 모두 적습니다.
  5) 회수기간은 누적 현금흐름이 0 이상이 되는 시점(그 해 안에서는 고르게 들어온다고 보고 소수로)이고,
     할인 회수기간도 같이 냅니다.
"""
import argparse
import csv
from collections import OrderedDict


def npv(rate, flows):
    return sum(cf / (1 + rate) ** t for t, cf in enumerate(flows))


def bisect(flows, lo, hi, tol=1e-7):
    f_lo = npv(lo, flows)
    for _ in range(200):
        mid = (lo + hi) / 2
        f_mid = npv(mid, flows)
        if abs(f_mid) < tol:
            break
        if f_lo * f_mid < 0:
            hi = mid
        else:
            lo, f_lo = mid, f_mid
    return (lo + hi) / 2


def irrs(flows):
    """-99%~1000% 를 촘촘히 훑어 NPV 부호가 바뀌는 칸마다 이분법으로 IRR을 찾습니다(여러 개일 수 있음)."""
    grid = [-0.99 + k * 0.005 for k in range(int((1.0 + 0.99) / 0.005) + 1)]   # -99% ~ 100%: 0.5%p 간격
    grid += [1.0 + k * 0.05 for k in range(1, 181)]                              # 100% ~ 1000%: 5%p 간격
    found = []
    prev_r, prev_v = grid[0], npv(grid[0], flows)
    for r in grid[1:]:
        v = npv(r, flows)
        if prev_v == 0:
            found.append(prev_r)
        elif prev_v * v < 0:
            found.append(bisect(flows, prev_r, r))
        prev_r, prev_v = r, v
    return found


def payback(flows, rate=None):
    cum = 0.0
    for t, cf in enumerate(flows):
        v = cf / (1 + rate) ** t if rate is not None else cf
        if t > 0 and cum < 0 <= cum + v:
            return t - 1 + (-cum / v)
        cum += v
    return None if cum < 0 else 0.0


def sign_changes(flows):
    signs = [cf > 0 for cf in flows if cf != 0]
    return sum(1 for a, b in zip(signs, signs[1:]) if a != b)


def main():
    p = argparse.ArgumentParser(description="투자안 NPV·IRR·회수기간 계산")
    p.add_argument("input", help="CSV: 안,기간,현금흐름 (기간 0 = 처음 투자, 음수)")
    p.add_argument("-r", "--rate", type=float, default=8.0, help="할인율 %% (기본 8)")
    p.add_argument("-o", "--output", default="npv_irr.out.csv")
    p.add_argument("--encoding", default="utf-8-sig")
    a = p.parse_args()

    plans = OrderedDict()
    with open(a.input, newline="", encoding=a.encoding) as f:
        for row in csv.DictReader(f):
            t = int(row["기간"])
            cf = float(str(row["현금흐름"]).replace(",", ""))
            plans.setdefault(row["안"].strip(), {})[t] = plans.get(row["안"].strip(), {}).get(t, 0) + cf

    rate = a.rate / 100
    rows = []
    for name, d in plans.items():
        flows = [d.get(t, 0.0) for t in range(max(d) + 1)]
        v = npv(rate, flows)
        found = irrs(flows)
        i = found[0] if len(found) == 1 else None
        pb, dpb = payback(flows), payback(flows, rate)
        invest = -sum(cf for cf in flows if cf < 0)
        note = []
        if sign_changes(flows) > 1:
            note.append("현금흐름 부호가 여러 번 바뀜")
        if len(found) > 1:
            note.append("IRR 여러 개(" + ", ".join(f"{x * 100:.2f}%" for x in found) + ") → NPV로 판단하세요")
        elif not found:
            note.append("IRR 없음(-99%~1000% 범위)")
        rows.append({
            "안": name, "기간(년)": len(flows) - 1, "총투자": round(invest), "현금흐름합": round(sum(flows)),
            f"NPV({a.rate:g}%)": round(v), "IRR(%)": round(i * 100, 2) if i is not None else "",
            "수익성지수(PI)": round((v + invest) / invest, 3) if invest else "",
            "회수기간(년)": round(pb, 2) if pb is not None else "회수 못 함",
            "할인회수기간(년)": round(dpb, 2) if dpb is not None else "회수 못 함",
            "판단": "채택 검토" if v > 0 else "기각 검토", "비고": "; ".join(note),
        })
    rows.sort(key=lambda r: -r[f"NPV({a.rate:g}%)"])
    with open(a.output, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"할인율 {a.rate:g}%, 투자안 {len(rows)}개 (NPV 큰 순) → {a.output}")
    for r in rows:
        irr_s = f"{r['IRR(%)']}%" if r["IRR(%)"] != "" else "-"
        pb = lambda x: f"{x}년" if isinstance(x, float) else x
        print(f"  {r['안']}: NPV {r[f'NPV({a.rate:g}%)']:,}원, IRR {irr_s}, 회수 {pb(r['회수기간(년)'])}"
              f" / 할인회수 {pb(r['할인회수기간(년)'])} → {r['판단']}" + (f"  ⚠ {r['비고']}" if r["비고"] else ""))


if __name__ == "__main__":
    main()
