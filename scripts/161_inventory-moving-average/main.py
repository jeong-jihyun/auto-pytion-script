"""입고·출고 기록으로 품목별 재고 수불부를 만들고, 이동평균법으로 출고원가와 기말재고 금액을 계산하는 스크립트.

생각의 흐름:
  1) ERP를 쓰지 않는 작은 창고나, ERP 결과를 검산하고 싶을 때 엑셀로 손계산하던 '재고 수불부'를 자동으로 만듭니다.
  2) 이동평균법은 '입고할 때마다 평균 단가를 다시 구하고, 출고는 그 시점의 평균 단가로 원가를 잡는' 방식입니다.
       새 평균단가 = (기존 재고금액 + 입고금액) ÷ (기존 수량 + 입고 수량)
       출고원가    = 출고 수량 × 그 시점 평균단가
  3) 기초재고(시작 수량·단가)는 따로 파일로 받을 수 있게 했습니다(--opening).
  4) 같은 날 입고와 출고가 섞이면 순서에 따라 원가가 달라집니다. 그래서 '일자 → 파일에 적힌 순서'로 처리하고,
     입고를 먼저 처리하고 싶으면 --in-first 를 주도록 했습니다.
  5) 재고보다 많이 출고하면(마이너스 재고) 계산을 멈추지 않고 '경고' 열에 표시해 사람이 확인하게 합니다.
  6) 돈 계산이라 float 대신 Decimal을 쓰고, 금액은 원 단위 반올림합니다.
"""
import argparse
import csv
from collections import OrderedDict
from decimal import Decimal, ROUND_HALF_UP

WON = Decimal("1")


def won(x):
    """원 단위 반올림."""
    return x.quantize(WON, rounding=ROUND_HALF_UP)


def read_csv(path, encoding):
    with open(path, newline="", encoding=encoding) as f:
        return list(csv.DictReader(f))


def main():
    p = argparse.ArgumentParser(description="이동평균법 재고 수불부 만들기")
    p.add_argument("movements", help="입출고 CSV (일자,품목,구분,수량,단가) - 구분은 입고/출고")
    p.add_argument("--opening", help="기초재고 CSV (품목,수량,단가)")
    p.add_argument("-o", "--output", default="ledger.out.csv", help="수불부 결과 CSV")
    p.add_argument("--summary", default="ledger_summary.out.csv", help="품목별 요약 CSV")
    p.add_argument("--in-first", action="store_true", help="같은 날이면 입고를 출고보다 먼저 처리")
    p.add_argument("--encoding", default="utf-8-sig")
    a = p.parse_args()

    # 품목별 상태: 수량, 금액(재고 금액은 소수 그대로 들고 다니다가 보여줄 때만 반올림)
    state = OrderedDict()
    summary = OrderedDict()

    def ensure(item):
        if item not in state:
            state[item] = {"qty": Decimal(0), "amt": Decimal(0)}
            summary[item] = {"기초수량": Decimal(0), "기초금액": Decimal(0), "입고수량": Decimal(0),
                             "입고금액": Decimal(0), "출고수량": Decimal(0), "출고원가": Decimal(0), "경고": 0}

    if a.opening:
        for r in read_csv(a.opening, a.encoding):
            item = r["품목"].strip()
            ensure(item)
            q, price = Decimal(r["수량"]), Decimal(r["단가"])
            state[item] = {"qty": q, "amt": q * price}
            summary[item]["기초수량"] = q
            summary[item]["기초금액"] = q * price

    rows = read_csv(a.movements, a.encoding)
    # 정렬 기준: 일자, (옵션) 입고 먼저, 원래 순서
    keyed = []
    for idx, r in enumerate(rows):
        kind = r["구분"].strip()
        order = 0 if (a.in_first and kind == "입고") else 1 if a.in_first else 0
        keyed.append((r["일자"].strip(), order, idx, r))
    keyed.sort(key=lambda t: t[:3])

    out = []
    for day, _, idx, r in keyed:
        item, kind = r["품목"].strip(), r["구분"].strip()
        q = Decimal(r["수량"])
        ensure(item)
        s = state[item]
        warn = ""
        in_amt = out_cost = Decimal(0)
        if kind == "입고":
            price = Decimal(r.get("단가") or "0")
            if price <= 0:
                warn = "입고 단가가 비어 있거나 0"
            in_amt = q * price
            s["qty"] += q
            s["amt"] += in_amt
            summary[item]["입고수량"] += q
            summary[item]["입고금액"] += in_amt
        elif kind == "출고":
            avg = s["amt"] / s["qty"] if s["qty"] > 0 else Decimal(0)
            if q > s["qty"]:
                warn = f"재고 부족(보유 {s['qty']} < 출고 {q})"
                summary[item]["경고"] += 1
            out_cost = q * avg
            s["qty"] -= q
            s["amt"] -= out_cost
            if s["qty"] <= 0:
                # 수량이 0이면 남은 자투리 금액을 없애고, 마이너스 재고면 금액도 0으로 둡니다
                # (마이너스 수량은 입고 누락 신호이므로 금액은 의미가 없습니다)
                s["amt"] = Decimal(0)
            summary[item]["출고수량"] += q
            summary[item]["출고원가"] += out_cost
        else:
            warn = f"알 수 없는 구분: {kind}"
            summary[item]["경고"] += 1
        avg_now = s["amt"] / s["qty"] if s["qty"] > 0 else Decimal(0)
        out.append({
            "일자": day, "품목": item, "구분": kind, "수량": q,
            "입고금액": won(in_amt), "출고원가": won(out_cost),
            "잔량": s["qty"], "평균단가": avg_now.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            "재고금액": won(s["amt"]), "경고": warn,
        })

    with open(a.output, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()) if out else ["일자"])
        w.writeheader()
        w.writerows(out)

    with open(a.summary, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["품목", "기초수량", "기초금액", "입고수량", "입고금액", "출고수량", "출고원가", "기말수량", "기말금액", "경고건수"])
        for item, sm in summary.items():
            st = state[item]
            w.writerow([item, sm["기초수량"], won(sm["기초금액"]), sm["입고수량"], won(sm["입고금액"]),
                        sm["출고수량"], won(sm["출고원가"]), st["qty"], won(st["amt"]), sm["경고"]])

    print(f"수불부 {len(out)}줄 → {a.output}, 품목 요약 {len(summary)}개 → {a.summary}")
    for item, sm in summary.items():
        st = state[item]
        flag = f"  ⚠ 경고 {sm['경고']}건" if sm["경고"] else ""
        print(f"  {item}: 출고원가 {won(sm['출고원가']):,}원, 기말 {st['qty']}개 / {won(st['amt']):,}원{flag}")


if __name__ == "__main__":
    main()
