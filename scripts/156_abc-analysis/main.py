"""품목별 매출(또는 사용량)로 ABC 분석(파레토 분석)을 해서 A·B·C 등급을 매기는 스크립트.

생각의 흐름:
  1) "매출의 80%는 품목 20%에서 나온다"는 파레토 법칙을 실제 데이터로 확인하는 방법이 ABC 분석입니다.
  2) 순서:
       ① 품목별 금액을 합칩니다(같은 품목이 여러 줄이면 더함).
       ② 금액이 큰 순으로 정렬하고 누적 비율을 구합니다.
       ③ 누적 비율이 A 기준(기본 80%) 이하까지 A, B 기준(기본 95%) 이하까지 B, 나머지는 C.
          ※ 기준선을 처음 넘는 품목은 그 등급에 넣습니다(80%를 걸치는 품목은 A).
  3) 금액 열 대신 수량 열로도 할 수 있게 --value 로 열 이름을 받습니다.
  4) 등급별 품목 수·금액 비중 요약을 화면에 보여 줍니다(재고 관리 집중 대상 선정용).
"""
import argparse
import csv
from collections import defaultdict


def main():
    p = argparse.ArgumentParser(description="ABC(파레토) 분석")
    p.add_argument("input")
    p.add_argument("--item", default="품목", help="품목 열")
    p.add_argument("--value", default="금액", help="기준 값 열(금액·수량 등)")
    p.add_argument("--a", type=float, default=80, help="A 누적 기준 %%(기본 80)")
    p.add_argument("--b", type=float, default=95, help="B 누적 기준 %%(기본 95)")
    p.add_argument("-o", "--output", default="abc.out.csv")
    a = p.parse_args()
    if not 0 < a.a < a.b <= 100:
        raise SystemExit("[오류] 0 < A기준 < B기준 <= 100 이어야 합니다")

    sums = defaultdict(float)
    for r in csv.DictReader(open(a.input, encoding="utf-8-sig")):
        try:
            sums[r[a.item].strip()] += float(r[a.value].replace(",", "") or 0)
        except ValueError:
            print(f"[건너뜀] 숫자 아님: {r}")
    items = sorted(sums.items(), key=lambda kv: kv[1], reverse=True)
    total = sum(v for _, v in items)
    if total <= 0:
        raise SystemExit("[오류] 합계가 0입니다")

    out, cum, prev_cum = [], 0.0, 0.0
    for rank, (name, v) in enumerate(items, 1):
        cum += v
        pct_before = prev_cum / total * 100     # 이 품목 '전까지'의 누적 비율
        grade = "A" if pct_before < a.a else "B" if pct_before < a.b else "C"
        out.append({"순위": rank, "품목": name, a.value: round(v, 2), "비중%": round(v / total * 100, 2),
                    "누적%": round(cum / total * 100, 2), "등급": grade})
        prev_cum = cum

    with open(a.output, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    print(f"품목 {len(out)}개 / 합계 {total:,.0f} → {a.output}")
    for g in "ABC":
        gs = [r for r in out if r["등급"] == g]
        share = sum(r[a.value] for r in gs) / total * 100
        print(f"  {g}등급: {len(gs)}개({len(gs)/len(out)*100:.0f}%) · {a.value} 비중 {share:.1f}%  "
              f"{', '.join(r['품목'] for r in gs[:5])}{' …' if len(gs) > 5 else ''}")


if __name__ == "__main__":
    main()
