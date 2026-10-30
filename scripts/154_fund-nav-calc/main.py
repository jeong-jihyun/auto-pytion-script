"""펀드(또는 모의 포트폴리오)의 일별 기준가격을 계산하고 전일 대비 등락·누적 수익률을 내는 스크립트.

생각의 흐름:
  1) 기준가격 = 순자산총액(자산 - 부채) ÷ 총 좌수 × 1,000 (국내 공모펀드 관행: 1,000좌 기준).
  2) 일별 입력 CSV에 날짜, 자산총액, 부채총액, 좌수를 적어 두면 날짜순으로 계산합니다.
  3) 설정(입금)·해지(출금)로 좌수가 바뀌어도 기준가격은 '1,000좌당 가치'라서 수익률 비교가 됩니다.
     그래서 순자산 증감과 기준가격 등락을 나란히 보여 주어 "돈이 들어와서 늘었는지,
     운용을 잘해서 늘었는지"를 구분할 수 있게 합니다.
  4) 소수점은 관행대로 기준가격 소수 둘째 자리 반올림(--digits 로 변경).
  5) 좌수가 0 이하이거나 순자산이 음수인 날은 계산하지 않고 경고로 남깁니다.
"""
import argparse
import csv
from decimal import Decimal, ROUND_HALF_UP


def d(s):
    return Decimal(str(s).replace(",", "").strip() or "0")


def main():
    p = argparse.ArgumentParser(description="펀드 기준가격(NAV) 계산")
    p.add_argument("input", help="CSV: 날짜,자산총액,부채총액,좌수")
    p.add_argument("--unit", type=int, default=1000, help="기준 좌수(기본 1000좌)")
    p.add_argument("--digits", type=int, default=2, help="기준가격 소수 자리(기본 2)")
    p.add_argument("-o", "--output", default="nav.out.csv")
    a = p.parse_args()

    q = Decimal(1).scaleb(-a.digits)
    rows = sorted(csv.DictReader(open(a.input, encoding="utf-8-sig")), key=lambda r: r["날짜"])
    out, warns = [], []
    first_nav = prev_nav = prev_net = None
    for r in rows:
        net = d(r["자산총액"]) - d(r["부채총액"])
        units = d(r["좌수"])
        if units <= 0 or net < 0:
            warns.append(f"{r['날짜']}: 좌수 {units} / 순자산 {net} → 계산 제외")
            continue
        nav = (net / units * a.unit).quantize(q, rounding=ROUND_HALF_UP)
        first_nav = first_nav or nav
        row = {"날짜": r["날짜"], "순자산총액": f"{net:f}", "좌수": f"{units:f}", "기준가격": f"{nav:f}",
               "전일대비": "", "등락률%": "", "누적수익률%": "", "순자산증감": "", "좌수증감": ""}
        if prev_nav is not None:
            row["전일대비"] = f"{nav - prev_nav:+f}"
            row["등락률%"] = f"{((nav / prev_nav - 1) * 100).quantize(Decimal('0.01'), ROUND_HALF_UP):+f}"
            row["순자산증감"] = f"{net - prev_net:+f}"
            row["좌수증감"] = f"{units - prev_units:+f}"
        row["누적수익률%"] = f"{((nav / first_nav - 1) * 100).quantize(Decimal('0.01'), ROUND_HALF_UP):+f}"
        out.append(row)
        prev_nav, prev_net, prev_units = nav, net, units

    with open(a.output, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()) if out else ["날짜"])
        w.writeheader()
        w.writerows(out)
    print(f"{len(out)}일 계산 → {a.output}")
    for r in out:
        print(f"  {r['날짜']} 기준가 {Decimal(r['기준가격']):,} ({(r['등락률%'] + '%') if r['등락률%'] else '첫날'}) "
              f"순자산증감 {r['순자산증감'] or '-'} / 좌수증감 {r['좌수증감'] or '-'}")
    for w_ in warns:
        print(f"[경고] {w_}")


if __name__ == "__main__":
    main()
