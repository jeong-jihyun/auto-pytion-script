"""여러 거래 상대방 사이의 주고받을 돈을 상계(네팅)해 최종 지급 목록을 만드는 스크립트.

예: A가 B에게 100, B가 A에게 70을 줘야 하면, 실제로는 A가 B에게 30만 보내면 됩니다.
생각의 흐름:
  1) 거래(보내는쪽, 받는쪽, 금액)를 읽어 통화별로 '사람별 순포지션(받을 돈 - 줄 돈)'을 구합니다.
  2) 두 사람씩 상계(양자 네팅) 결과를 만듭니다.
  3) 추가로 전체를 한 번에 상계(다자 네팅)해, 줄 사람과 받을 사람을 큰 금액부터 짝지어
     송금 건수를 줄인 지급 목록을 만듭니다.
  4) 순포지션의 합은 항상 0이어야 하므로 이를 검산합니다.
"""
import argparse
import csv
import sys
from collections import defaultdict
from decimal import Decimal
from pathlib import Path


def read(path, cols):
    f, t, amt, cur = cols
    trades = []
    with path.open(newline="", encoding="utf-8-sig") as fp:
        for ln, r in enumerate(csv.DictReader(fp), start=2):
            v = Decimal((r[amt] or "0").replace(",", ""))
            if v < 0:
                print(f"[주의] {ln}줄 음수 금액은 방향을 바꿔 처리합니다")
                r[f], r[t], v = r[t], r[f], -v
            trades.append((r[f].strip(), r[t].strip(), v, (r.get(cur) or "KRW").strip()))
    return trades


def bilateral(trades):
    pair = defaultdict(Decimal)
    for payer, payee, v, cur in trades:
        a, b = sorted([payer, payee])
        pair[(cur, a, b)] += v if payer == a else -v  # +면 a가 b에게 줌
    out = []
    for (cur, a, b), v in sorted(pair.items()):
        if v > 0:
            out.append({"통화": cur, "보내는쪽": a, "받는쪽": b, "금액": str(v)})
        elif v < 0:
            out.append({"통화": cur, "보내는쪽": b, "받는쪽": a, "금액": str(-v)})
    return out


def multilateral(trades):
    net = defaultdict(Decimal)  # (통화, 사람) -> 받을 돈 - 줄 돈
    for payer, payee, v, cur in trades:
        net[(cur, payer)] -= v
        net[(cur, payee)] += v
    by_cur = defaultdict(dict)
    for (cur, who), v in net.items():
        by_cur[cur][who] = v
    payments, positions = [], []
    for cur, people in sorted(by_cur.items()):
        if sum(people.values()) != 0:
            raise RuntimeError(f"{cur} 순포지션 합계가 0이 아닙니다(데이터 확인)")
        for who, v in sorted(people.items()):
            positions.append({"통화": cur, "상대방": who, "순포지션": str(v)})
        payers = sorted([[w, -v] for w, v in people.items() if v < 0], key=lambda x: -x[1])
        payees = sorted([[w, v] for w, v in people.items() if v > 0], key=lambda x: -x[1])
        i = j = 0
        while i < len(payers) and j < len(payees):
            amt = min(payers[i][1], payees[j][1])
            payments.append({"통화": cur, "보내는쪽": payers[i][0], "받는쪽": payees[j][0], "금액": str(amt)})
            payers[i][1] -= amt
            payees[j][1] -= amt
            if payers[i][1] == 0:
                i += 1
            if payees[j][1] == 0:
                j += 1
    return positions, payments


def write(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.DictWriter(fp, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main():
    p = argparse.ArgumentParser(description="정산 상계(네팅)")
    p.add_argument("input", type=Path)
    p.add_argument("--from-col", default="보내는쪽")
    p.add_argument("--to-col", default="받는쪽")
    p.add_argument("--amount-col", default="금액")
    p.add_argument("--currency-col", default="통화")
    p.add_argument("-d", "--outdir", type=Path, default=Path("output"))
    a = p.parse_args()

    trades = read(a.input, (a.from_col, a.to_col, a.amount_col, a.currency_col))
    bi = bilateral(trades)
    try:
        pos, multi = multilateral(trades)
    except RuntimeError as e:
        print(f"[오류] {e}")
        sys.exit(1)
    write(a.outdir / "netting_bilateral.csv", bi, ["통화", "보내는쪽", "받는쪽", "금액"])
    write(a.outdir / "netting_positions.csv", pos, ["통화", "상대방", "순포지션"])
    write(a.outdir / "netting_payments.csv", multi, ["통화", "보내는쪽", "받는쪽", "금액"])
    print(f"원거래 {len(trades)}건 → 양자 상계 {len(bi)}건 → 다자 상계 {len(multi)}건 (결과: {a.outdir})")


if __name__ == "__main__":
    main()
