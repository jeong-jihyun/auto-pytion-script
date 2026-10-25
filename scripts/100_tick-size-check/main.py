"""주문 파일의 가격이 호가단위에 맞는지 미리 검사하는 스크립트(참고용 점검).

생각의 흐름:
  1) 주문 CSV(종목,가격,수량)를 읽습니다.
  2) 가격대에 맞는 호가단위를 표에서 찾고, 가격이 그 단위의 배수인지 확인합니다.
  3) 수량이 1 이상의 정수인지도 같이 봅니다.
  4) 틀린 줄은 이유와 함께 보여 주고, 가장 가까운 올바른 가격(내림)을 제안합니다.
  호가단위 표는 --market 에 따라 다르며 코드 위쪽 표에 모아 두었습니다.
  주의: 표는 참고용입니다. 실제 규정은 반드시 거래소 공시로 확인하세요.
"""
import argparse
import csv
from decimal import Decimal
from pathlib import Path

# (가격 미만, 호가단위). 마지막 줄은 그 이상 모두에 적용
TABLES = {
    "kospi": [(2000, 1), (5000, 5), (20000, 10), (50000, 50), (200000, 100), (500000, 500), (None, 1000)],
    "kosdaq": [(2000, 1), (5000, 5), (20000, 10), (50000, 50), (None, 100)],
}


def tick_for(price, table):
    for limit, tick in table:
        if limit is None or price < limit:
            return tick


def main():
    p = argparse.ArgumentParser(description="호가단위 검사")
    p.add_argument("--input", required=True, help="CSV(종목,가격,수량)")
    p.add_argument("--market", choices=list(TABLES), default="kospi")
    p.add_argument("--out", default="output/호가검사.csv")
    a = p.parse_args()
    table = TABLES[a.market]

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    bad = total = 0
    with open(a.input, encoding="utf-8-sig", newline="") as f, \
            open(out, "w", encoding="utf-8-sig", newline="") as o:
        w = csv.writer(o)
        w.writerow(["줄", "종목", "가격", "수량", "결과", "이유", "제안가격"])
        for n, r in enumerate(csv.DictReader(f), start=2):
            total += 1
            reasons, suggest = [], ""
            try:
                price = Decimal(r["가격"].replace(",", ""))
                tick = tick_for(price, table)
                if price <= 0 or price % tick != 0:
                    reasons.append(f"호가단위 {tick}원의 배수가 아님")
                    suggest = int(price // tick * tick) if price > 0 else ""
            except Exception:
                reasons.append("가격이 숫자가 아님")
            try:
                q = Decimal(r["수량"].replace(",", ""))
                if q < 1 or q != q.to_integral_value():
                    reasons.append("수량은 1 이상의 정수여야 함")
            except Exception:
                reasons.append("수량이 숫자가 아님")
            if reasons:
                bad += 1
            w.writerow([n, r["종목"], r["가격"], r["수량"], "오류" if reasons else "정상", "; ".join(reasons), suggest])
    print(f"{a.market}: 총 {total}건 중 오류 {bad}건 -> {out}")


if __name__ == "__main__":
    main()
