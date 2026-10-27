"""고정금리 채권의 수익률 ↔ 가격, 경과이자, 듀레이션을 계산하는 스크립트.

생각의 흐름:
  1) 채권 가격은 '앞으로 받을 이자와 원금'을 수익률로 할인해 더한 값입니다.
  2) 만기일에서 거꾸로 (12 ÷ 연 지급횟수)개월씩 빼며 이자 지급일을 만들고,
     결제일 바로 앞 지급일(직전)과 바로 뒤 지급일(다음)을 찾습니다.
  3) 다음 지급일까지 남은 비율 w = (다음 - 결제일) ÷ (다음 - 직전) 를 구하고
       가격(경과이자 포함, dirty) = Σ 이자 ÷ (1 + y/f)^(w + k)  +  액면 ÷ (1 + y/f)^(w + n - 1)
       경과이자 = 1회 이자 × (결제일 - 직전) ÷ (다음 - 직전)
       단가(clean) = dirty - 경과이자
  4) 수익률이 주어지면 가격을, 단가가 주어지면 수익률을 '반씩 좁혀 찾기(이분법)'로 거꾸로 구합니다.
     가격은 수익률이 오르면 반드시 내려가므로(단조), 이분법이 확실하게 답을 찾습니다.
  5) 금리 위험 지표: 맥컬리 듀레이션(평균 회수 기간, 년), 수정 듀레이션(금리 1%p 변할 때 가격 변화율 %).
  ※ 교육·검산용 단순 모형입니다. 실제 시가평가(민평)·세금·영업일 조정과는 다를 수 있습니다.
"""
import argparse
import calendar
import csv
from datetime import date, datetime
from pathlib import Path


def add_months(d, m):
    y, mo = divmod(d.month - 1 + m, 12)
    y += d.year
    mo += 1
    return date(y, mo, min(d.day, calendar.monthrange(y, mo)[1]))


def schedule(settle, maturity, freq):
    """결제일 이후 남은 지급일 목록과 직전 지급일."""
    step = 12 // freq
    dates, k = [], 0
    while True:
        d = add_months(maturity, -step * k)
        if d <= settle:
            return d, sorted(dates)
        dates.append(d)
        k += 1


def analyze(face, coupon, freq, settle, maturity, y):
    prev, coupons = schedule(settle, maturity, freq)
    nxt, n = coupons[0], len(coupons)
    w = (nxt - settle).days / (nxt - prev).days
    c = face * coupon / freq
    dirty, weighted = 0.0, 0.0
    for k in range(n):
        cf = c + (face if k == n - 1 else 0)
        pv = cf / (1 + y / freq) ** (w + k)
        dirty += pv
        weighted += pv * (w + k) / freq
    accrued = c * (settle - prev).days / (nxt - prev).days
    mac = weighted / dirty
    return {"dirty": dirty, "accrued": accrued, "clean": dirty - accrued,
            "mac": mac, "mod": mac / (1 + y / freq), "next": nxt, "n": n}


def solve_yield(face, coupon, freq, settle, maturity, clean):
    lo, hi = -0.05, 1.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if analyze(face, coupon, freq, settle, maturity, mid)["clean"] > clean:
            lo = mid  # 가격이 너무 높다 → 수익률을 올려야 함
        else:
            hi = mid
    return (lo + hi) / 2


def d(s):
    return datetime.strptime(s.strip(), "%Y-%m-%d").date()


def main():
    p = argparse.ArgumentParser(description="채권 수익률↔단가, 경과이자, 듀레이션")
    p.add_argument("bonds", type=Path, help="CSV(종목,표면금리,지급횟수,결제일,만기일,수익률,단가) - 수익률·단가 중 하나만")
    p.add_argument("--face", type=float, default=10000, help="액면(기본 10,000원 기준 단가)")
    p.add_argument("-o", "--output", type=Path, default=Path("output/bond_result.csv"))
    a = p.parse_args()

    out = []
    with a.bonds.open(newline="", encoding="utf-8-sig") as fp:
        for r in csv.DictReader(fp):
            cpn, freq = float(r["표면금리"]) / 100, int(r["지급횟수"])
            settle, mat = d(r["결제일"]), d(r["만기일"])
            if 12 % freq or mat <= settle:
                print(f"[건너뜀] {r['종목']}: 지급횟수(1,2,4,12) 또는 날짜 확인")
                continue
            if (r.get("수익률") or "").strip():
                y = float(r["수익률"]) / 100
                how = "수익률→단가"
            else:
                y = solve_yield(a.face, cpn, freq, settle, mat, float(r["단가"].replace(",", "")))
                how = "단가→수익률"
            res = analyze(a.face, cpn, freq, settle, mat, y)
            out.append([r["종목"], how, f"{y * 100:.4f}", f"{res['clean']:.2f}", f"{res['accrued']:.2f}",
                        f"{res['dirty']:.2f}", res["next"], res["n"], f"{res['mac']:.4f}", f"{res['mod']:.4f}"])
            print(f"{r['종목']:<10} {how}: 수익률 {y * 100:.4f}% | 단가 {res['clean']:,.2f} "
                  f"+ 경과이자 {res['accrued']:,.2f} = {res['dirty']:,.2f} | 수정듀레이션 {res['mod']:.3f}")
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["종목", "계산", "수익률%", "단가(clean)", "경과이자", "가격(dirty)", "다음지급일",
                    "남은지급횟수", "맥컬리듀레이션(년)", "수정듀레이션"])
        w.writerows(out)
    print(f"-> {a.output} (액면 {a.face:,.0f} 기준)")


if __name__ == "__main__":
    main()
