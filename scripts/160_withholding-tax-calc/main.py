"""프리랜서·강사료 등 지급액에 대해 원천징수 세액(사업소득 3.3%, 기타소득 8.8%)과 실수령액을 계산하는 스크립트.

생각의 흐름:
  1) 회사가 개인에게 돈을 줄 때 자주 쓰는 두 가지 원천징수를 다룹니다.
       - 사업소득(인적용역, 예: 프리랜서 디자인·개발): 소득세 3% + 지방소득세(소득세의 10%) = 3.3%
       - 기타소득(예: 일시적 강연료·원고료): 필요경비 60%를 뺀 '기타소득금액'에
         소득세 20% + 지방소득세 2% → 지급액 기준 약 8.8%
  2) 세액 끝자리는 실무 관행대로 10원 미만을 버립니다(--truncate 로 1원 단위 등 변경 가능).
     지방소득세는 '버린 뒤의 소득세' × 10% 로 계산합니다.
  3) 작은 금액 처리 규칙도 옵션으로 둡니다.
       - 기타소득 과세최저한: 건별 기타소득금액이 5만 원 이하면 세금 0 (--other-min, 기본 50000)
       - 소액부징수: 소득세가 1,000원 미만이면 징수하지 않음 (--small-exempt 를 줄 때만 적용)
     법령은 바뀔 수 있어 기준 금액·적용 여부를 옵션으로 열어 두었습니다.
  4) "실수령액을 얼마로 맞춰 달라"는 요청이 많아서, --reverse 를 주면 '실수령액'에서
     지급액(세전)을 거꾸로 찾아 줍니다(1원씩 맞춰 가며 실수령액이 목표 이상이 되는 가장 작은 지급액).
"""
import argparse
import csv


def taxes(gross, kind, a):
    """(소득세, 지방소득세) 를 돌려줍니다."""
    t = a.truncate
    if kind == "사업":
        income_tax = gross * 3 // 100
    elif kind == "기타":
        other_income = gross - gross * a.expense_rate // 100   # 필요경비 차감
        if other_income <= a.other_min:
            return 0, 0
        income_tax = other_income * 20 // 100
    else:
        raise ValueError(f"구분은 '사업' 또는 '기타' 이어야 합니다: {kind}")
    income_tax = income_tax // t * t
    if a.small_exempt and income_tax < 1000:
        return 0, 0
    local_tax = income_tax // 10 // t * t
    return income_tax, local_tax


def gross_from_net(net, kind, a):
    """실수령액 net 이상이 되는 가장 작은 지급액을 찾습니다."""
    rate = 0.033 if kind == "사업" else 0.088
    g = max(net, int(net / (1 - rate)) - 100)
    while True:
        it, lt = taxes(g, kind, a)
        if g - it - lt >= net:
            # 한 칸 아래도 되는지 확인해 최소값을 보장
            while g > net:
                it2, lt2 = taxes(g - 1, kind, a)
                if g - 1 - it2 - lt2 >= net:
                    g -= 1
                else:
                    break
            return g
        g += 1


def main():
    p = argparse.ArgumentParser(description="원천징수(3.3%/8.8%) 계산")
    p.add_argument("input", help="CSV: 이름,구분(사업/기타),금액")
    p.add_argument("--reverse", action="store_true", help="금액 열을 '실수령액'으로 보고 지급액을 역산")
    p.add_argument("--truncate", type=int, default=10, help="세액 절사 단위(기본 10원)")
    p.add_argument("--expense-rate", type=int, default=60, help="기타소득 필요경비율%% (기본 60)")
    p.add_argument("--other-min", type=int, default=50000, help="기타소득 과세최저한(기본 5만 원)")
    p.add_argument("--small-exempt", action="store_true", help="소득세 1,000원 미만 소액부징수 적용")
    p.add_argument("-o", "--output", default="withholding.out.csv")
    a = p.parse_args()

    out = []
    for r in csv.DictReader(open(a.input, encoding="utf-8-sig")):
        kind = r["구분"].strip().replace("소득", "")
        amt = int(r["금액"].replace(",", "").strip())
        gross = gross_from_net(amt, kind, a) if a.reverse else amt
        it, lt = taxes(gross, kind, a)
        out.append({"이름": r["이름"], "구분": kind + "소득", "지급액": gross, "소득세": it,
                    "지방소득세": lt, "원천징수합계": it + lt, "실수령액": gross - it - lt,
                    "실효세율%": round((it + lt) / gross * 100, 2) if gross else 0})

    with open(a.output, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()) if out else ["이름"])
        w.writeheader()
        w.writerows(out)
    print(f"{'역산' if a.reverse else '계산'} {len(out)}건 → {a.output}")
    for r in out:
        print(f"  {r['이름']} [{r['구분']}] 지급 {r['지급액']:,} - 소득세 {r['소득세']:,} - 지방 {r['지방소득세']:,}"
              f" = 실수령 {r['실수령액']:,}원 ({r['실효세율%']}%)")
    tot = {k: sum(r[k] for r in out) for k in ("지급액", "소득세", "지방소득세", "실수령액")}
    print(f"  합계: 지급 {tot['지급액']:,} / 소득세 {tot['소득세']:,} / 지방소득세 {tot['지방소득세']:,} / 실수령 {tot['실수령액']:,}")


if __name__ == "__main__":
    main()
