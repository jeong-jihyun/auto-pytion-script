"""선입선출(FIFO) 방식으로 매도 때 실현손익을 계산하는 스크립트.

입력 열: 일자, 종목, 구분(매수/매도), 수량, 단가
매도 수량만큼 가장 먼저 산 물량부터 차례로 짝지어 손익을 계산합니다.
- 실현손익 = (매도단가 - 매수단가) x 수량 - 매도 수수료/세금(--sell-cost-rate 비율)
- 남은 보유 수량(평균 단가 포함)도 따로 저장합니다.
보유보다 많이 파는 줄(공매도 형태)은 오류로 보고하고 계산에서 뺍니다.
세금 신고용이 아니라 점검용 계산입니다.
"""
import argparse
import csv
import sys
from collections import defaultdict, deque
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description="FIFO 실현손익 계산")
    p.add_argument("input", type=Path)
    p.add_argument("--sell-cost-rate", type=float, default=0.0,
                   help="매도금액에 붙는 비용 비율(%%), 예: 0.2")
    p.add_argument("-o", "--output-dir", type=Path, default=Path("output"))
    a = p.parse_args()

    with a.input.open(newline="", encoding="utf-8-sig") as fp:
        rows = list(csv.DictReader(fp))
    rows.sort(key=lambda r: r["일자"])           # 일자 순(같은 날은 입력 순서 유지)

    lots = defaultdict(deque)                    # 종목 -> [[수량, 단가], ...]
    realized, errors = [], []
    for n, r in enumerate(rows, start=2):
        try:
            qty, price = int(r["수량"].replace(",", "")), float(r["단가"].replace(",", ""))
        except ValueError:
            errors.append(f"수량/단가를 읽을 수 없음: {r}")
            continue
        sym, side = r["종목"], r["구분"].strip()
        if side == "매수":
            lots[sym].append([qty, price])
        elif side == "매도":
            if qty > sum(l[0] for l in lots[sym]):
                errors.append(f"{r['일자']} {sym} 매도 {qty}주가 보유보다 많음 -> 제외")
                continue
            left = qty
            while left > 0:
                lot = lots[sym][0]
                take = min(left, lot[0])
                cost = price * take * a.sell_cost_rate / 100
                pnl = (price - lot[1]) * take - cost
                realized.append([r["일자"], sym, take, lot[1], price, round(cost), round(pnl)])
                lot[0] -= take
                left -= take
                if lot[0] == 0:
                    lots[sym].popleft()
        else:
            errors.append(f"구분은 매수/매도만 가능: {r}")

    a.output_dir.mkdir(parents=True, exist_ok=True)
    with (a.output_dir / "realized.csv").open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["매도일자", "종목", "수량", "매수단가", "매도단가", "비용", "실현손익"])
        w.writerows(realized)
    with (a.output_dir / "holdings.csv").open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["종목", "보유수량", "평균단가"])
        for sym, dq in sorted(lots.items()):
            q = sum(l[0] for l in dq)
            if q:
                w.writerow([sym, q, round(sum(l[0] * l[1] for l in dq) / q, 2)])

    by_sym = defaultdict(float)
    for r in realized:
        by_sym[r[1]] += r[6]
    for sym, v in sorted(by_sym.items()):
        print(f"  {sym}: 실현손익 {v:,.0f}원")
    print(f"[완료] 총 실현손익 {sum(by_sym.values()):,.0f}원 -> {a.output_dir}/realized.csv, holdings.csv")
    for e in errors:
        print("[확인 필요]", e)


if __name__ == "__main__":
    main()
