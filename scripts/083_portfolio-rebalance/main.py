"""보유 종목을 목표 비중에 맞추려면 무엇을 몇 주 사고팔아야 하는지 계산하는 스크립트(리밸런싱 계산기).

생각의 흐름:
  1) 현재 평가금액 = 보유수량 × 현재가, 총자산 = 평가금액 합계 + 현금(+추가 입금).
  2) 목표금액 = 총자산 × 목표비중. 차이 = 목표금액 - 현재 평가금액.
  3) 차이가 작으면(--band, 예: 목표 비중 ±2%p 이내) 거래하지 않습니다. 잦은 매매·수수료를 줄이기 위해서입니다.
  4) 거래 수량은 '주' 단위라 소수점 아래를 버립니다.
     - 매도를 먼저 계산해 현금을 만들고, 그 현금 안에서 매수합니다(현금이 마이너스가 되지 않게).
     - 수수료율(--fee)을 반영해 매수 가능 수량을 줄입니다.
  5) 거래 후 예상 비중과 남는 현금을 보여 줍니다. 실제 주문은 하지 않습니다.
"""
import argparse
import csv
import math
from pathlib import Path


def num(x):
    return float((x or "0").replace(",", "").replace("%", "").strip() or 0)


def main():
    p = argparse.ArgumentParser(description="목표 비중 리밸런싱 수량 계산")
    p.add_argument("holdings", type=Path, help="CSV(종목,보유수량,현재가,목표비중%)")
    p.add_argument("--cash", type=float, default=0, help="현재 현금")
    p.add_argument("--deposit", type=float, default=0, help="이번에 추가로 넣을 돈")
    p.add_argument("--band", type=float, default=2.0, help="허용 오차(비중 %p). 이내면 거래 안 함")
    p.add_argument("--fee", type=float, default=0.015, help="수수료율 %(매수·매도 각각)")
    p.add_argument("-o", "--output", type=Path, default=Path("output/rebalance.csv"))
    a = p.parse_args()

    with a.holdings.open(newline="", encoding="utf-8-sig") as fp:
        rows = list(csv.DictReader(fp))
    for r in rows:
        r["qty"], r["price"], r["target"] = num(r["보유수량"]), num(r["현재가"]), num(r["목표비중%"])
        r["value"] = r["qty"] * r["price"]
    tsum = sum(r["target"] for r in rows)
    if abs(tsum - 100) > 0.01:
        print(f"  ! 목표비중 합계가 {tsum}% 입니다(100%가 아님). 남는 비중은 현금으로 둡니다.")
    cash = a.cash + a.deposit
    total = sum(r["value"] for r in rows) + cash
    fee = a.fee / 100
    for r in rows:
        r["now_w"] = r["value"] / total * 100 if total else 0
        r["gap"] = total * r["target"] / 100 - r["value"]
        r["trade"] = 0
    # 1단계: 매도(비중 초과분) — 현금을 만듭니다.
    for r in rows:
        if r["now_w"] - r["target"] > a.band and r["price"] > 0:
            n = min(r["qty"], math.floor(-r["gap"] / r["price"]))
            r["trade"] = -n
            cash += n * r["price"] * (1 - fee)
    # 2단계: 매수(비중 부족분) — 부족한 비율이 큰 종목부터, 현금 안에서.
    for r in sorted(rows, key=lambda x: x["now_w"] - x["target"]):
        if r["target"] - r["now_w"] > a.band and r["price"] > 0:
            n = math.floor(min(r["gap"], cash / (1 + fee)) / r["price"])
            if n > 0:
                r["trade"] = n
                cash -= n * r["price"] * (1 + fee)

    out = []
    for r in rows:
        after = (r["qty"] + r["trade"]) * r["price"]
        out.append({"종목": r["종목"], "현재가": int(r["price"]), "보유수량": int(r["qty"]),
                    "현재비중%": round(r["now_w"], 2), "목표비중%": r["target"],
                    "주문": "매수" if r["trade"] > 0 else ("매도" if r["trade"] < 0 else "유지"),
                    "수량": abs(int(r["trade"])), "거래금액": int(abs(r["trade"]) * r["price"]),
                    "거래후비중%": round(after / total * 100, 2) if total else 0})
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.DictWriter(fp, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    print(f"총자산 {total:,.0f}원 (현금 {a.cash + a.deposit:,.0f}원 포함), 허용오차 ±{a.band}%p → {a.output}")
    for x in out:
        act = f"{x['주문']} {x['수량']}주({x['거래금액']:,}원)" if x["수량"] else "유지"
        print(f"  - {x['종목']}: {x['현재비중%']}% → {x['거래후비중%']}% (목표 {x['목표비중%']}%) {act}")
    print(f"  거래 후 예상 현금: {cash:,.0f}원 (수수료 {a.fee}% 반영, 세금 미반영)")


if __name__ == "__main__":
    main()
