"""전일 잔고 + 당일 체결·입출고 = 당일 잔고 인지 계좌·종목별로 검증하는 스크립트(증권 잔고 롤포워드).

생각의 흐름:
  1) 증권 시스템 일 마감 때 '잔고가 맞나?'는 가장 기본 점검입니다.
     계산식: 기대 잔고 = 전일 잔고 + 매수 수량 - 매도 수량 + 입고 - 출고
  2) 이 기대 잔고를 실제 당일 잔고 파일(시스템 또는 예탁 기관 잔고)과 비교합니다.
  3) 계좌번호+종목코드를 한 쌍(키)으로 묶습니다. 세 파일 중 어디에만 있는 키도 빠짐없이 봅니다.
       - 전일 잔고가 없고 오늘 처음 산 종목 → 전일 0으로 봄
       - 기대 잔고가 0인데 당일 잔고 파일에 줄이 없음 → 정상(전량 매도)
  4) 결과 상태
       일치 / 수량차이 / 당일잔고없음(기대>0인데 줄 없음) / 마이너스(기대 잔고가 음수 → 공매도·체결 누락 의심)
  5) 수량은 소수(펀드 좌수)가 있을 수 있어 Decimal 로 정확히 계산합니다.
"""
import argparse
import csv
from collections import defaultdict
from decimal import Decimal
from pathlib import Path


def dec(s):
    s = str(s or "0").replace(",", "").strip()
    return Decimal(s or "0")


def read_qty(path, qty_col):
    out = defaultdict(Decimal)
    with path.open(newline="", encoding="utf-8-sig") as fp:
        for r in csv.DictReader(fp):
            out[(r["계좌번호"].strip(), r["종목코드"].strip())] += dec(r[qty_col])
    return out


def fmt(d):
    d = d.normalize()
    return f"{d:,f}" if d != d.to_integral() else f"{int(d):,}"


def main():
    p = argparse.ArgumentParser(description="증권 잔고 롤포워드 검증")
    p.add_argument("--prev", type=Path, required=True, help="전일 잔고 CSV(계좌번호,종목코드,수량)")
    p.add_argument("--moves", type=Path, required=True, help="당일 변동 CSV(계좌번호,종목코드,구분(매수/매도/입고/출고),수량)")
    p.add_argument("--today", type=Path, required=True, help="당일 잔고 CSV(계좌번호,종목코드,수량)")
    p.add_argument("-o", "--output", type=Path, default=Path("output/position_check.csv"))
    p.add_argument("--all", action="store_true", help="일치한 줄도 결과 파일에 포함")
    a = p.parse_args()

    prev = read_qty(a.prev, "수량")
    today = read_qty(a.today, "수량")
    sign = {"매수": 1, "입고": 1, "매도": -1, "출고": -1}
    buy, sell, inq, outq = (defaultdict(Decimal) for _ in range(4))
    unknown = 0
    with a.moves.open(newline="", encoding="utf-8-sig") as fp:
        for r in csv.DictReader(fp):
            k = (r["계좌번호"].strip(), r["종목코드"].strip())
            kind, q = r["구분"].strip(), dec(r["수량"])
            if kind not in sign:
                unknown += 1
                print(f"[경고] 알 수 없는 구분 '{kind}' → 건너뜀: {k}")
                continue
            {"매수": buy, "매도": sell, "입고": inq, "출고": outq}[kind][k] += q

    keys = sorted(set(prev) | set(today) | set(buy) | set(sell) | set(inq) | set(outq))
    rows, cnt = [], defaultdict(int)
    for k in keys:
        exp = prev[k] + buy[k] - sell[k] + inq[k] - outq[k]
        has_today = k in today
        act = today[k]
        if exp < 0:
            st = "마이너스"
        elif exp == act:
            st = "일치"
        elif not has_today and exp > 0:
            st = "당일잔고없음"
        else:
            st = "수량차이"
        cnt[st] += 1
        if st != "일치" or a.all:
            rows.append([k[0], k[1], fmt(prev[k]), fmt(buy[k]), fmt(sell[k]), fmt(inq[k]), fmt(outq[k]),
                         fmt(exp), fmt(act) if has_today else "", fmt(act - exp), st])

    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["계좌번호", "종목코드", "전일", "매수", "매도", "입고", "출고", "기대잔고", "당일잔고", "차이(당일-기대)", "상태"])
        w.writerows(rows)
    print(f"계좌·종목 {len(keys)}쌍 점검: " + ", ".join(f"{s} {n}" for s, n in sorted(cnt.items())))
    if unknown:
        print(f"알 수 없는 구분 {unknown}건은 계산에서 빠졌습니다")
    print(f"저장: {a.output}")


if __name__ == "__main__":
    main()
