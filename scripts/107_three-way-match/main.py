"""발주(PO)·입고(GR)·청구(Invoice) 세 장부를 맞춰 보는 '3자 대사(3-way match)' 스크립트.

생각의 흐름(구매·회계 담당자가 대금 지급 전에 확인하는 순서):
  1) 세 파일을 (발주번호, 품목코드) 로 묶습니다. 입고·청구는 여러 번 나뉠 수 있으므로 수량·금액을 합칩니다.
  2) 수량 점검: 청구수량 ≤ 입고수량 ≤ 발주수량 이어야 합니다.
     - 입고 > 발주 : 과입고          - 청구 > 입고 : 입고 안 된 물건 청구(지급 보류 대상)
  3) 단가 점검: 청구단가가 발주단가와 허용오차(--price-tol, 기본 0%)보다 다르면 '단가 차이'.
  4) 한쪽에만 있는 건(발주 없는 청구 등)도 따로 표시합니다.
  5) 문제없으면 '지급 가능', 있으면 '지급 보류'로 판정합니다.
"""
import argparse
import csv
from collections import defaultdict
from pathlib import Path


def num(x):
    return float((x or "0").replace(",", "").strip() or 0)


def load(path, qty_col, price_col=None):
    data = defaultdict(lambda: [0.0, 0.0])  # 수량, 금액
    with path.open(newline="", encoding="utf-8-sig") as fp:
        for r in csv.DictReader(fp):
            k = (r["발주번호"].strip(), r["품목코드"].strip())
            q = num(r[qty_col])
            data[k][0] += q
            if price_col:
                data[k][1] += q * num(r[price_col])
    return data


def main():
    p = argparse.ArgumentParser(description="발주·입고·청구 3자 대사")
    p.add_argument("po", type=Path, help="발주 CSV(발주번호,품목코드,발주수량,발주단가)")
    p.add_argument("gr", type=Path, help="입고 CSV(발주번호,품목코드,입고수량)")
    p.add_argument("inv", type=Path, help="청구 CSV(발주번호,품목코드,청구수량,청구단가)")
    p.add_argument("--price-tol", type=float, default=0.0, help="단가 허용오차 %")
    p.add_argument("-o", "--output", type=Path, default=Path("output/three_way_match.csv"))
    a = p.parse_args()

    po = load(a.po, "발주수량", "발주단가")
    gr = load(a.gr, "입고수량")
    inv = load(a.inv, "청구수량", "청구단가")
    keys = sorted(set(po) | set(gr) | set(inv))
    out, hold, hold_amt = [], 0, 0.0
    for k in keys:
        pq, pa = po.get(k, (0, 0))
        gq = gr.get(k, (0, 0))[0]
        iq, ia = inv.get(k, (0, 0))
        pu = pa / pq if pq else 0
        iu = ia / iq if iq else 0
        probs = []
        if k not in po:
            probs.append("발주 없음")
        if k in inv and k not in gr:
            probs.append("입고 없이 청구")
        if gq > pq and k in po:
            probs.append(f"과입고({gq:g}>{pq:g})")
        if iq > gq and k in gr:
            probs.append(f"입고보다 많이 청구({iq:g}>{gq:g})")
        if pu and iu and abs(iu - pu) / pu * 100 > a.price_tol:
            probs.append(f"단가 차이(발주 {pu:,.0f} / 청구 {iu:,.0f})")
        if k in po and k not in inv:
            state = "청구 대기"
        else:
            state = "지급 보류" if probs else "지급 가능"
        if state == "지급 보류":
            hold += 1
            hold_amt += ia
        out.append([k[0], k[1], pq, gq, iq, round(pu), round(iu), round(ia), state, " / ".join(probs)])
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["발주번호", "품목코드", "발주수량", "입고수량", "청구수량", "발주단가", "청구단가", "청구금액", "판정", "문제"])
        w.writerows(out)
    print(f"{len(out)}줄 대사, 지급 보류 {hold}줄(청구 {hold_amt:,.0f}원) → {a.output}")
    for r in out:
        if r[8] != "지급 가능":
            print(f"  - {r[0]}/{r[1]}: {r[8]} {r[9]}".rstrip())


if __name__ == "__main__":
    main()
