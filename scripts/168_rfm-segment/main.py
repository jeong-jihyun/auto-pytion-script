"""주문 내역으로 고객별 RFM(최근성·빈도·금액) 점수를 매기고, 고객을 몇 개 무리로 나누는 스크립트.

생각의 흐름:
  1) '누가 좋은 고객인가'를 감으로 고르지 않고 세 가지 숫자로 봅니다.
       R(Recency)  : 마지막 주문 후 며칠 지났나 (짧을수록 좋음)
       F(Frequency): 몇 번 주문했나            (많을수록 좋음)
       M(Monetary) : 모두 얼마 썼나            (클수록 좋음)
  2) 숫자 크기가 업종마다 달라서 절대 기준 대신 '고객들 사이 순위'로 1~5점을 줍니다(5분위).
     같은 값은 같은 점수가 되도록 평균 순위를 씁니다.
  3) 점수 조합으로 이해하기 쉬운 이름의 무리를 붙입니다. 규칙은 위에서부터 먼저 맞는 것:
       핵심 고객   : R≥4, F≥4, M≥4
       이탈 위험   : R≤2, F≥3 (자주 샀는데 요즘 안 옴 → '충성'보다 먼저 확인해야 놓치지 않음)
       충성 고객   : F≥4
       신규 고객   : R≥4, F≤1 (최근에 처음 산 사람)
       휴면 고객   : R≤1
       관심 필요   : 그 밖
  4) 기준일(--as-of)이 없으면 데이터의 마지막 주문일 다음 날로 잡아, 언제 돌려도 같은 결과가 나오게 했습니다.
"""
import argparse
import csv
from collections import Counter, OrderedDict
from datetime import date, timedelta

SEGMENTS = ["핵심 고객", "이탈 위험", "충성 고객", "신규 고객", "휴면 고객", "관심 필요"]
ACTIONS = {
    "핵심 고객": "감사 혜택·VIP 관리", "충성 고객": "추가 구매 제안", "신규 고객": "두 번째 구매 유도",
    "이탈 위험": "재방문 쿠폰·연락", "휴면 고객": "저비용 재활성화 메시지(수신동의자만)", "관심 필요": "관찰",
}


def scores(values, higher_better=True, bins=5):
    """값 목록 → 1~bins 점수(평균 순위 기반 분위)."""
    n = len(values)
    order = sorted(range(n), key=lambda i: values[i])
    ranks = [0.0] * n
    i = 0
    while i < n:  # 같은 값 묶음에 평균 순위
        j = i
        while j + 1 < n and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    out = []
    for r in ranks:
        s = min(bins, int((r - 0.5) / n * bins) + 1)   # 1..bins
        out.append(s if higher_better else bins + 1 - s)
    return out


def segment(r, f, m):
    if r >= 4 and f >= 4 and m >= 4:
        return "핵심 고객"
    if r <= 2 and f >= 3:
        return "이탈 위험"
    if f >= 4:
        return "충성 고객"
    if r >= 4 and f <= 1:
        return "신규 고객"
    if r <= 1:
        return "휴면 고객"
    return "관심 필요"


def main():
    p = argparse.ArgumentParser(description="고객 RFM 점수·무리 나누기")
    p.add_argument("orders", help="주문 CSV (고객ID,주문일,금액)")
    p.add_argument("--customer", default="고객ID")
    p.add_argument("--date", default="주문일")
    p.add_argument("--amount", default="금액")
    p.add_argument("--as-of", help="기준일 YYYY-MM-DD (기본: 마지막 주문일 다음 날)")
    p.add_argument("--since", help="이 날짜 이후 주문만 사용(예: 최근 1년)")
    p.add_argument("-o", "--output", default="rfm.out.csv")
    p.add_argument("--encoding", default="utf-8-sig")
    a = p.parse_args()

    cust = OrderedDict()
    since = date.fromisoformat(a.since) if a.since else None
    with open(a.orders, newline="", encoding=a.encoding) as f:
        for row in csv.DictReader(f):
            d = date.fromisoformat(row[a.date].strip()[:10])
            if since and d < since:
                continue
            amt = float(str(row[a.amount]).replace(",", "") or 0)
            c = cust.setdefault(row[a.customer].strip(), {"last": d, "freq": 0, "money": 0.0})
            c["last"] = max(c["last"], d)
            c["freq"] += 1
            c["money"] += amt
    if not cust:
        raise SystemExit("주문이 없습니다.")
    as_of = date.fromisoformat(a.as_of) if a.as_of else max(c["last"] for c in cust.values()) + timedelta(days=1)

    ids = list(cust)
    rec = [(as_of - cust[i]["last"]).days for i in ids]
    rs = scores(rec, higher_better=False)
    fs = scores([cust[i]["freq"] for i in ids])
    ms = scores([cust[i]["money"] for i in ids])

    rows = []
    for k, i in enumerate(ids):
        seg = segment(rs[k], fs[k], ms[k])
        rows.append({"고객ID": i, "마지막주문": cust[i]["last"].isoformat(), "경과일": rec[k],
                     "주문수": cust[i]["freq"], "총금액": round(cust[i]["money"]),
                     "R": rs[k], "F": fs[k], "M": ms[k], "RFM": f"{rs[k]}{fs[k]}{ms[k]}",
                     "무리": seg, "제안": ACTIONS[seg]})
    rows.sort(key=lambda r: (SEGMENTS.index(r["무리"]), -r["총금액"]))
    with open(a.output, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    total = sum(r["총금액"] for r in rows)
    cnt = Counter(r["무리"] for r in rows)
    print(f"기준일 {as_of}, 고객 {len(rows)}명 → {a.output}")
    for s in SEGMENTS:
        if cnt[s]:
            money = sum(r["총금액"] for r in rows if r["무리"] == s)
            print(f"  {s:<6} {cnt[s]:>3}명  매출 비중 {money / total * 100:5.1f}%  → {ACTIONS[s]}")


if __name__ == "__main__":
    main()
