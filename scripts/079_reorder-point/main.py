"""재고와 사용량을 보고 발주가 필요한 품목과 권장 발주 수량을 계산하는 스크립트.

생각의 흐름(ERP의 재주문점 방식):
  1) 하루 평균 사용량 = 최근 사용량 합계 / 기간 일수
  2) 재주문점 = 하루 평균 사용량 × 조달기간(일) + 안전재고
  3) (현재고 + 발주잔량) 이 재주문점 이하이면 '발주 필요'
  4) 권장 발주량 = 목표재고(재주문점 + 하루 사용량 × 보충일수) - (현재고 + 발주잔량),
     최소발주단위(MOQ)·포장단위에 맞춰 올림
  5) 남은 재고로 며칠 버틸 수 있는지(소진 예상일)도 함께 보여 줍니다.
"""
import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path


def f(x, default=0.0):
    x = (x or "").replace(",", "").strip()
    return float(x) if x else default


def main():
    p = argparse.ArgumentParser(description="재주문점·권장 발주량 계산")
    p.add_argument("stock", type=Path, help="재고 CSV(품목코드,품목명,현재고,발주잔량,안전재고,조달일수,최소발주량,포장단위)")
    p.add_argument("usage", type=Path, help="사용 내역 CSV(일자,품목코드,수량)")
    p.add_argument("--days", type=int, default=30, help="사용량 평균 기간(일)")
    p.add_argument("--cover-days", type=int, default=14, help="발주 시 채워 둘 추가 일수")
    p.add_argument("-o", "--output", type=Path, default=Path("output/reorder.csv"))
    a = p.parse_args()

    used = defaultdict(float)
    with a.usage.open(newline="", encoding="utf-8-sig") as fp:
        for r in csv.DictReader(fp):
            used[r["품목코드"].strip()] += f(r["수량"])

    out, need = [], 0
    with a.stock.open(newline="", encoding="utf-8-sig") as fp:
        for r in csv.DictReader(fp):
            code = r["품목코드"].strip()
            daily = used[code] / a.days
            on_hand, on_order = f(r["현재고"]), f(r.get("발주잔량"))
            rop = daily * f(r["조달일수"]) + f(r.get("안전재고"))
            avail = on_hand + on_order
            qty = 0
            if avail <= rop and daily > 0:
                target = rop + daily * a.cover_days
                qty = max(target - avail, f(r.get("최소발주량")))
                pack = f(r.get("포장단위"), 1) or 1
                qty = math.ceil(qty / pack) * pack
                need += 1
            status = "발주 필요" if qty else ("사용 없음" if daily == 0 else "충분")
            cover = round(on_hand / daily, 1) if daily else ""
            out.append({"품목코드": code, "품목명": r["품목명"], "하루평균사용": round(daily, 2),
                        "현재고": on_hand, "발주잔량": on_order, "재주문점": round(rop, 1),
                        "판정": status, "권장발주량": int(qty), "남은일수": cover})
    out.sort(key=lambda x: (x["판정"] != "발주 필요", x["남은일수"] if x["남은일수"] != "" else 1e9))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.DictWriter(fp, fieldnames=list(out[0].keys()) if out else ["품목코드"])
        w.writeheader()
        w.writerows(out)
    print(f"품목 {len(out)}개 중 발주 필요 {need}개 → {a.output}")
    for x in out[:need]:
        print(f"  - {x['품목명']}: 권장 {x['권장발주량']}개 (남은 {x['남은일수']}일)")


if __name__ == "__main__":
    main()
