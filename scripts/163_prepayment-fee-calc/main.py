"""대출을 만기 전에 갚을 때 내는 중도상환수수료를 '잔존기간 체감 방식'으로 계산하는 스크립트.

생각의 흐름:
  1) 우리나라 은행 대출의 중도상환수수료는 보통 이렇게 계산합니다.
       수수료 = 중도상환 금액 × 수수료율 × (남은 일수 ÷ 기준 일수)
     - 기준 기간: 대출일부터 '수수료 면제 시점'까지. 면제 시점은 보통 대출 후 3년이고,
       만기가 3년보다 짧으면 만기일까지입니다.
     - 남은 일수: 상환일부터 면제 시점까지의 일수. 0 이하면(이미 3년 지남) 수수료 0원.
  2) 대출마다 수수료율·면제 기간이 달라 CSV 열로 받고, 빈칸이면 옵션 기본값을 씁니다.
  3) "얼마를 지금 갚을까"를 고민할 때 쓰도록, 수수료를 뺀 '실제 갚는 데 드는 돈'과
     '앞으로 아낄 이자(대략)'도 함께 보여 줍니다. 아낄 이자는 남은 만기까지 단순 이자로 어림합니다.
  4) 날짜 계산은 표준 라이브러리 date만 쓰고, 'N년 뒤'는 같은 월·일로(2월 29일은 28일로) 맞춥니다.
"""
import argparse
import csv
from datetime import date


def parse_date(s):
    return date.fromisoformat(s.strip().replace(".", "-").replace("/", "-"))


def add_years(d, n):
    try:
        return d.replace(year=d.year + n)
    except ValueError:  # 2월 29일
        return d.replace(year=d.year + n, day=28)


def calc(row, a):
    start = parse_date(row["대출일"])
    maturity = parse_date(row["만기일"])
    repay = parse_date(row["상환일"])
    amount = int(str(row["상환금액"]).replace(",", ""))
    rate = float(row.get("수수료율") or a.rate)           # %
    free_years = int(row.get("면제기간") or a.free_years)    # 년
    loan_rate = float(row.get("대출금리") or 0)             # %, 아낄 이자 어림용

    if repay < start:
        raise ValueError("상환일이 대출일보다 빠릅니다")
    end = min(maturity, add_years(start, free_years))       # 수수료가 붙는 마지막 날
    base_days = (end - start).days
    remain_days = max((end - repay).days, 0)
    fee = 0
    if base_days > 0 and remain_days > 0:
        fee = amount * rate / 100 * remain_days / base_days
        fee = int(fee) // a.truncate * a.truncate
    saved = 0
    if loan_rate and repay < maturity:
        saved = int(amount * loan_rate / 100 * (maturity - repay).days / 365)
    return {
        "대출ID": row.get("대출ID", ""), "상환금액": amount, "수수료율(%)": rate,
        "면제시점": end.isoformat(), "기준일수": base_days, "남은일수": remain_days,
        "중도상환수수료": fee, "수수료포함 필요금액": amount + fee,
        "아낄이자(어림)": saved, "이득(어림)": saved - fee if loan_rate else "",
    }


def main():
    p = argparse.ArgumentParser(description="중도상환수수료 계산(잔존기간 체감 방식)")
    p.add_argument("input", help="CSV: 대출ID,대출일,만기일,상환일,상환금액[,수수료율,면제기간,대출금리]")
    p.add_argument("-o", "--output", default="prepay_fee.out.csv")
    p.add_argument("--rate", type=float, default=1.2, help="수수료율 기본값 %% (기본 1.2)")
    p.add_argument("--free-years", type=int, default=3, help="수수료 면제까지 기간(년, 기본 3)")
    p.add_argument("--truncate", type=int, default=10, help="이 단위 미만 버림(기본 10원)")
    p.add_argument("--encoding", default="utf-8-sig")
    a = p.parse_args()

    with open(a.input, newline="", encoding=a.encoding) as f:
        rows = list(csv.DictReader(f))
    results, errors = [], 0
    for r in rows:
        try:
            results.append(calc(r, a))
        except (ValueError, KeyError) as e:
            errors += 1
            print(f"  ✗ {r.get('대출ID', '?')}: 계산 못 함 - {e}")
    if results:
        with open(a.output, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(results[0].keys()))
            w.writeheader()
            w.writerows(results)
    print(f"계산 {len(results)}건, 오류 {errors}건 → {a.output}")
    for x in results:
        gain = f", 이득(어림) {x['이득(어림)']:,}원" if x["이득(어림)"] != "" else ""
        print(f"  {x['대출ID']}: {x['상환금액']:,}원 상환 → 수수료 {x['중도상환수수료']:,}원"
              f" (남은 {x['남은일수']}/{x['기준일수']}일){gain}")


if __name__ == "__main__":
    main()
