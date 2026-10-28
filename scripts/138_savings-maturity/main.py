"""정기예금·적금의 만기 이자, 세금, 실수령액을 계산하고 여러 상품을 한 표로 비교하는 스크립트.

생각의 흐름:
  1) '연 3.5% 적금'이라도 실제 이자는 생각보다 적습니다. 적금은 매달 넣은 돈마다 맡긴 기간이 달라서
     첫 달 돈은 n개월, 마지막 달 돈은 1개월만 이자가 붙기 때문입니다.
  2) 계산식(연이율 r, 개월 n, 월이율 m = r/12)
       예금 단리   : 원금 × r × n/12
       예금 월복리 : 원금 × ((1+m)^n - 1)
       적금 단리   : 월납입 × m × n(n+1)/2          ← 1~n개월 이자를 모두 더한 값
       적금 월복리 : Σ(k=1..n) 월납입 × ((1+m)^k - 1)
  3) 세금은 과세 구분으로 정합니다.
       일반 15.4%(소득세 14% + 지방소득세 1.4%), 세금우대 9.5%, 비과세 0%, 또는 숫자(예: 1.4 → 1.4%)
     세율·제도는 바뀔 수 있으니 가입 전 은행 안내를 꼭 확인합니다.
     세금은 10원 미만을 버립니다(원천징수 관행). 은행마다 끝자리 처리 방식이 조금 다를 수 있습니다.
  4) 상품 하나는 명령줄로, 여러 개는 CSV로 받아 실수령 이자가 큰 순서로 비교표를 만듭니다.
"""
import argparse
import csv
import math
from pathlib import Path

TAX = {"일반": 0.154, "세금우대": 0.095, "비과세": 0.0}


def interest(kind, method, amount, rate, months):
    m = rate / 12
    if kind == "예금":
        if method == "단리":
            return amount * rate * months / 12
        return amount * ((1 + m) ** months - 1)
    if method == "단리":
        return amount * m * months * (months + 1) / 2
    return sum(amount * ((1 + m) ** k - 1) for k in range(1, months + 1))


def tax_rate_of(name, tax_type):
    if tax_type in TAX:
        return TAX[tax_type]
    try:
        return float(tax_type.rstrip("%")) / 100
    except ValueError:
        raise ValueError(f"{name}: 과세는 {'/'.join(TAX)} 또는 숫자(%)로 적어 주세요") from None


def calc(name, kind, method, amount, rate_pct, months, tax_type):
    if kind not in ("예금", "적금") or method not in ("단리", "월복리"):
        raise ValueError(f"{name}: 종류는 예금/적금, 방식은 단리/월복리 중 하나")
    tax_rate = tax_rate_of(name, tax_type)
    # 0.1+0.2 같은 소수 오차로 299999.9999 가 되어 1원 덜 나오는 일을 막으려고 반올림 후 버림
    gross = math.floor(round(interest(kind, method, amount, rate_pct / 100, months), 6))
    tax = math.floor(round(gross * tax_rate, 6) / 10) * 10
    principal = amount if kind == "예금" else amount * months
    net = gross - tax
    eff = net / principal * 12 / months * 100 if kind == "예금" else None
    return {"상품": name, "종류": kind, "방식": method, "납입(원금)": principal, "연이율(%)": rate_pct,
            "개월": months, "과세": tax_type, "세전이자": gross, "세금": tax, "세후이자": net,
            "만기수령액": principal + net,
            "세후연수익률(%)": round(eff, 3) if eff is not None else ""}


def won(s):
    return int(str(s).replace(",", "").strip())


def main():
    p = argparse.ArgumentParser(description="예금·적금 만기 계산·비교")
    p.add_argument("--csv", type=Path, help="여러 상품 CSV(상품,종류,방식,금액,연이율,개월,과세)")
    p.add_argument("--kind", choices=["예금", "적금"], help="한 상품 계산 시: 예금(한 번에) / 적금(매달)")
    p.add_argument("--method", choices=["단리", "월복리"], default="단리")
    p.add_argument("--amount", help="예금은 원금, 적금은 월 납입액(원)")
    p.add_argument("--rate", type=float, help="연이율(%)")
    p.add_argument("--months", type=int, help="기간(개월)")
    p.add_argument("--tax", default="일반", help="일반/세금우대/비과세 또는 세율 숫자(%%)")
    p.add_argument("-o", "--output", type=Path, default=Path("output/savings_compare.csv"))
    a = p.parse_args()

    results = []
    if a.csv:
        with a.csv.open(newline="", encoding="utf-8-sig") as fp:
            for r in csv.DictReader(fp):
                results.append(calc(r["상품"], r["종류"].strip(), r["방식"].strip(), won(r["금액"]),
                                    float(r["연이율"]), int(r["개월"]), (r.get("과세") or "일반").strip()))
    elif a.kind and a.amount and a.rate is not None and a.months:
        results.append(calc("입력 상품", a.kind, a.method, won(a.amount), a.rate, a.months, a.tax))
    else:
        raise SystemExit("[오류] --csv 또는 --kind --amount --rate --months 를 주세요")

    results.sort(key=lambda x: x["세후이자"], reverse=True)
    for r in results:
        print(f"{r['상품']}: {r['종류']} {r['방식']} {r['연이율(%)']}% {r['개월']}개월 / 원금 {r['납입(원금)']:,}원"
              f" → 세전 {r['세전이자']:,} − 세금 {r['세금']:,} = 세후 {r['세후이자']:,}원, 만기 {r['만기수령액']:,}원")
    if a.csv:
        a.output.parent.mkdir(parents=True, exist_ok=True)
        with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
            w = csv.DictWriter(fp, fieldnames=list(results[0]))
            w.writeheader()
            w.writerows(results)
        print(f"저장(세후이자 큰 순): {a.output}")


if __name__ == "__main__":
    try:
        main()
    except ValueError as e:
        raise SystemExit(f"[오류] {e}")
