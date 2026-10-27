"""주문 내역과 체결 내역을 주문번호로 맞춰 보는(대사) 스크립트.

생각의 흐름:
  1) 증권·거래 시스템에서는 '주문 1건 = 체결 여러 건'이 흔합니다. 장 마감 후 둘이 맞는지 확인해야 합니다.
  2) 체결을 주문번호별로 모아 체결수량 합계와 평균 체결가(수량가중)를 구합니다.
  3) 주문마다 상태를 정합니다.
       전량체결 : 체결수량 합 = 주문수량
       부분체결 : 0 < 체결수량 합 < 주문수량
       미체결   : 체결 없음
  4) 있으면 안 되는 일을 '문제'로 따로 모읍니다.
       과체결          : 체결수량 합 > 주문수량
       주문없는체결    : 체결의 주문번호가 주문 내역에 없음
       지정가위반      : 지정가 매수인데 주문가보다 비싸게, 매도인데 주문가보다 싸게 체결
       종목/계좌 다름은 주문 쪽 정보를 기준으로 삼으므로 체결 파일에는 주문번호만 있으면 됩니다.
  5) 금액은 Decimal 로 계산해 소수점 오차를 없앱니다.
"""
import argparse
import csv
import sys
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


def dec(s):
    return Decimal(str(s).replace(",", "").strip() or "0")


def main():
    p = argparse.ArgumentParser(description="주문-체결 대사")
    p.add_argument("orders", type=Path, help="주문 CSV(주문번호,계좌,종목,매매,주문유형,주문수량,주문가격)")
    p.add_argument("fills", type=Path, help="체결 CSV(체결번호,주문번호,체결수량,체결가격,체결시각)")
    p.add_argument("-o", "--outdir", type=Path, default=Path("output"))
    a = p.parse_args()

    orders = {}
    with a.orders.open(newline="", encoding="utf-8-sig") as fp:
        for r in csv.DictReader(fp):
            orders[r["주문번호"].strip()] = r
    fills = defaultdict(list)
    issues = []
    with a.fills.open(newline="", encoding="utf-8-sig") as fp:
        for r in csv.DictReader(fp):
            oid = r["주문번호"].strip()
            if oid not in orders:
                issues.append(["주문없는체결", oid, r["체결번호"], f"체결 {r['체결수량']}주 @ {r['체결가격']}"])
                continue
            fills[oid].append(r)

    status_rows, counts = [], defaultdict(int)
    for oid, o in orders.items():
        oq, op = dec(o["주문수량"]), dec(o["주문가격"])
        side, otype = o["매매"].strip(), o["주문유형"].strip()
        fq = sum((dec(f["체결수량"]) for f in fills[oid]), Decimal(0))
        amt = sum((dec(f["체결수량"]) * dec(f["체결가격"]) for f in fills[oid]), Decimal(0))
        avg = (amt / fq).quantize(Decimal("0.01"), ROUND_HALF_UP) if fq else ""
        if fq == 0:
            st = "미체결"
        elif fq < oq:
            st = "부분체결"
        elif fq == oq:
            st = "전량체결"
        else:
            st = "과체결"
            issues.append(["과체결", oid, "", f"주문 {oq}주인데 체결 합계 {fq}주"])
        if otype == "지정가":
            for f in fills[oid]:
                fp_ = dec(f["체결가격"])
                if (side == "매수" and fp_ > op) or (side == "매도" and fp_ < op):
                    issues.append(["지정가위반", oid, f["체결번호"], f"{side} 지정가 {op}인데 {fp_}에 체결"])
        counts[st] += 1
        status_rows.append([oid, o["계좌"], o["종목"], side, otype, oq, op, fq, oq - fq, avg, len(fills[oid]), st])

    a.outdir.mkdir(parents=True, exist_ok=True)
    with (a.outdir / "order_status.csv").open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["주문번호", "계좌", "종목", "매매", "주문유형", "주문수량", "주문가격",
                    "체결수량", "미체결수량", "평균체결가", "체결건수", "상태"])
        w.writerows(status_rows)
    with (a.outdir / "issues.csv").open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["문제", "주문번호", "체결번호", "내용"])
        w.writerows(issues)

    print("주문 상태: " + ", ".join(f"{k} {v}건" for k, v in counts.items()))
    for i in issues:
        print(f"  [문제:{i[0]}] 주문 {i[1]} {('체결 ' + i[2]) if i[2] else ''} - {i[3]}")
    print(f"문제 {len(issues)}건 -> {a.outdir}/order_status.csv, issues.csv")
    sys.exit(1 if issues else 0)


if __name__ == "__main__":
    main()
