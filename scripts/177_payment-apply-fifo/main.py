"""거래처 입금액을 오래된 미수 채권(청구서)부터 차례로 갚은 것으로 맞춰(선입선출 충당)
청구서별 남은 잔액과 남는 입금(선수금)을 계산하는 스크립트.

생각의 흐름:
  1) 거래처가 '청구서 번호 없이' 한꺼번에 입금하면 어느 청구서를 갚은 건지 정해야 합니다.
     흔한 회사 규칙은 '오래된 청구서부터 먼저 갚는다(FIFO)' 입니다.
  2) 거래처별로 청구서를 청구일(같으면 번호) 순서로 줄 세우고, 입금도 입금일 순서로 줄 세웁니다.
  3) 입금 하나를 들고 맨 앞 청구서의 잔액부터 깎습니다. 다 갚으면 다음 청구서로 넘어가고,
     입금이 남으면 다음 청구서를 계속 깎습니다. 청구서가 모두 갚아졌는데 입금이 남으면 '선수금'입니다.
  4) 결과는 세 파일입니다: 충당 내역(어느 입금이 어느 청구서를 얼마 갚았나), 청구서별 잔액, 거래처 요약.
  5) 039번(채권 연령 분석)에 넣기 전에 이 스크립트로 잔액을 먼저 맞추면 편합니다.
"""
import argparse
import csv
import os
from collections import defaultdict
from decimal import Decimal


def money(v):
    return Decimal((v or "0").replace(",", "").strip() or "0")


def read(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write(path, rows, fields):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser(description="입금액을 오래된 청구서부터 충당(FIFO)")
    ap.add_argument("invoices", help="청구서 CSV (거래처,청구번호,청구일,금액)")
    ap.add_argument("payments", help="입금 CSV (거래처,입금번호,입금일,금액)")
    ap.add_argument("-o", "--outdir", default="out")
    args = ap.parse_args()

    inv_by = defaultdict(list)
    for r in read(args.invoices):
        inv_by[r["거래처"].strip()].append({"청구번호": r["청구번호"], "청구일": r["청구일"],
                                          "금액": money(r["금액"]), "잔액": money(r["금액"])})
    pay_by = defaultdict(list)
    for r in read(args.payments):
        pay_by[r["거래처"].strip()].append({"입금번호": r["입금번호"], "입금일": r["입금일"], "금액": money(r["금액"])})

    applied, balances, summary = [], [], []
    for cust in sorted(set(inv_by) | set(pay_by)):
        invs = sorted(inv_by[cust], key=lambda x: (x["청구일"], x["청구번호"]))
        pays = sorted(pay_by[cust], key=lambda x: (x["입금일"], x["입금번호"]))
        idx = 0
        advance = Decimal("0")
        for p in pays:
            left = p["금액"]
            while left > 0 and idx < len(invs):
                inv = invs[idx]
                use = min(left, inv["잔액"])
                if use > 0:
                    inv["잔액"] -= use
                    left -= use
                    applied.append({"거래처": cust, "입금번호": p["입금번호"], "입금일": p["입금일"],
                                    "청구번호": inv["청구번호"], "청구일": inv["청구일"], "충당액": use,
                                    "청구서잔액": inv["잔액"]})
                if inv["잔액"] == 0:
                    idx += 1
            if left > 0:
                advance += left
                applied.append({"거래처": cust, "입금번호": p["입금번호"], "입금일": p["입금일"],
                                "청구번호": "(선수금)", "청구일": "", "충당액": left, "청구서잔액": ""})
        for inv in invs:
            st = "완납" if inv["잔액"] == 0 else ("일부입금" if inv["잔액"] < inv["금액"] else "미입금")
            balances.append({"거래처": cust, "청구번호": inv["청구번호"], "청구일": inv["청구일"],
                             "청구액": inv["금액"], "입금충당": inv["금액"] - inv["잔액"], "잔액": inv["잔액"], "상태": st})
        summary.append({"거래처": cust, "청구합계": sum((i["금액"] for i in invs), Decimal("0")),
                        "입금합계": sum((p["금액"] for p in pays), Decimal("0")),
                        "미수잔액": sum((i["잔액"] for i in invs), Decimal("0")), "선수금": advance})

    os.makedirs(args.outdir, exist_ok=True)
    write(os.path.join(args.outdir, "applied.csv"), applied, list(applied[0].keys()) if applied else ["거래처"])
    write(os.path.join(args.outdir, "invoice_balance.csv"), balances, list(balances[0].keys()) if balances else ["거래처"])
    write(os.path.join(args.outdir, "customer_summary.csv"), summary, list(summary[0].keys()) if summary else ["거래처"])

    print(f"거래처 {len(summary)}곳, 청구서 {len(balances)}건, 충당 내역 {len(applied)}줄")
    for s in summary:
        # 검산: 청구 - 입금 = 미수 - 선수금 이어야 합니다
        ok = s["청구합계"] - s["입금합계"] == s["미수잔액"] - s["선수금"]
        print(f"  {s['거래처']}: 청구 {s['청구합계']:,} / 입금 {s['입금합계']:,} → 미수 {s['미수잔액']:,}, "
              f"선수금 {s['선수금']:,} {'(검산 OK)' if ok else '(검산 불일치!)'}")
    print(f"결과 → {args.outdir}/applied.csv, invoice_balance.csv, customer_summary.csv")


if __name__ == "__main__":
    main()
