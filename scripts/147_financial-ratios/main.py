"""재무제표 요약 CSV로 주요 재무비율(안정성·수익성·활동성)을 계산하는 스크립트.

생각의 흐름:
  1) 거래처 신용 검토, 투자 검토, 사업계획 보고 때 '유동비율, 부채비율, ROE…'를 매번 계산기로 두드립니다.
  2) 입력은 '항목, 기간1, 기간2 …' 형태(행=계정, 열=연도)로 받습니다. 회계 자료가 보통 이렇게 생겼기 때문입니다.
  3) 계정 이름이 회사마다 조금씩 달라서, 자주 쓰는 이름 몇 개를 같은 뜻으로 묶어 찾습니다
     (예: '자본총계' = '자본', '총자본').
  4) 계산하는 비율
       - 안정성: 유동비율, 당좌비율, 부채비율, 자기자본비율, 이자보상배율
       - 수익성: 매출총이익률, 영업이익률, 순이익률, ROA, ROE
       - 활동성: 총자산회전율, 매출채권회전일수, 재고자산회전일수
       - 성장성: 매출액증가율, 영업이익증가율 (앞 기간이 있을 때)
     ROA·ROE 는 앞 기간이 있으면 '평균 자산/자본'으로, 없으면 기말 값으로 계산합니다.
  5) 필요한 계정이 없거나 분모가 0이면 그 비율은 '-' 로 두고 이유를 알려 줍니다.
"""
import argparse
import csv

ALIASES = {
    "유동자산": ["유동자산"],
    "재고자산": ["재고자산", "재고"],
    "매출채권": ["매출채권", "매출채권및기타채권"],
    "자산총계": ["자산총계", "총자산", "자산"],
    "유동부채": ["유동부채"],
    "부채총계": ["부채총계", "총부채", "부채"],
    "자본총계": ["자본총계", "총자본", "자본"],
    "매출액": ["매출액", "매출", "영업수익"],
    "매출원가": ["매출원가"],
    "영업이익": ["영업이익", "영업이익(손실)"],
    "이자비용": ["이자비용", "금융비용"],
    "당기순이익": ["당기순이익", "당기순이익(손실)", "순이익"],
}


def load(path, encoding):
    with open(path, encoding=encoding, newline="") as f:
        rows = list(csv.reader(f))
    periods = [c.strip() for c in rows[0][1:]]
    raw = {}
    for r in rows[1:]:
        if not r or not r[0].strip():
            continue
        key = r[0].replace(" ", "").strip()
        vals = []
        for c in r[1:]:
            c = c.replace(",", "").strip()
            if c.startswith("(") and c.endswith(")"):  # (1,000) 은 음수
                c = "-" + c[1:-1]
            vals.append(float(c) if c else None)
        raw[key] = vals
    data = {}
    for std, names in ALIASES.items():
        for n in names:
            if n in raw:
                data[std] = raw[n]
                break
    return periods, data


def main():
    p = argparse.ArgumentParser(description="재무비율 계산")
    p.add_argument("input", help="재무제표 요약 CSV (첫 열=계정, 다음 열=기간)")
    p.add_argument("-o", "--output", default="ratios.out.csv")
    p.add_argument("--encoding", default="utf-8-sig")
    a = p.parse_args()

    periods, d = load(a.input, a.encoding)
    missing = [k for k in ALIASES if k not in d]
    if missing:
        print(f"[안내] 찾지 못한 계정: {', '.join(missing)} → 이 계정이 필요한 비율은 '-' 로 나옵니다")

    def v(name, i):
        vals = d.get(name)
        return vals[i] if vals and i < len(vals) else None

    def div(x, y, mul=100):
        if x is None or y in (None, 0):
            return None
        return x / y * mul

    def avg(name, i):
        cur, prev = v(name, i), v(name, i - 1) if i > 0 else None
        if cur is None:
            return None
        return (cur + prev) / 2 if prev is not None else cur

    defs = [
        ("안정성", "유동비율(%)", lambda i: div(v("유동자산", i), v("유동부채", i))),
        ("안정성", "당좌비율(%)", lambda i: div(None if v("유동자산", i) is None else v("유동자산", i) - (v("재고자산", i) or 0), v("유동부채", i))),
        ("안정성", "부채비율(%)", lambda i: div(v("부채총계", i), v("자본총계", i))),
        ("안정성", "자기자본비율(%)", lambda i: div(v("자본총계", i), v("자산총계", i))),
        ("안정성", "이자보상배율(배)", lambda i: div(v("영업이익", i), v("이자비용", i), 1)),
        ("수익성", "매출총이익률(%)", lambda i: div(None if v("매출액", i) is None or v("매출원가", i) is None else v("매출액", i) - v("매출원가", i), v("매출액", i))),
        ("수익성", "영업이익률(%)", lambda i: div(v("영업이익", i), v("매출액", i))),
        ("수익성", "순이익률(%)", lambda i: div(v("당기순이익", i), v("매출액", i))),
        ("수익성", "ROA(%)", lambda i: div(v("당기순이익", i), avg("자산총계", i))),
        ("수익성", "ROE(%)", lambda i: div(v("당기순이익", i), avg("자본총계", i))),
        ("활동성", "총자산회전율(회)", lambda i: div(v("매출액", i), avg("자산총계", i), 1)),
        ("활동성", "매출채권회전일수(일)", lambda i: div(avg("매출채권", i), v("매출액", i), 365)),
        ("활동성", "재고자산회전일수(일)", lambda i: div(avg("재고자산", i), v("매출원가", i), 365)),
        ("성장성", "매출액증가율(%)", lambda i: None if i == 0 or v("매출액", i - 1) is None or v("매출액", i) is None else div(v("매출액", i) - v("매출액", i - 1), abs(v("매출액", i - 1)) or None)),
        ("성장성", "영업이익증가율(%)", lambda i: None if i == 0 or v("영업이익", i - 1) is None or v("영업이익", i) is None else div(v("영업이익", i) - v("영업이익", i - 1), abs(v("영업이익", i - 1)) or None)),
    ]

    table = []
    for group, name, fn in defs:
        table.append([group, name] + ["-" if (x := fn(i)) is None else f"{x:,.2f}" for i in range(len(periods))])

    with open(a.output, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["구분", "비율"] + periods)
        w.writerows(table)

    print(f"{'구분':6s} {'비율':20s}" + "".join(f"{p:>12s}" for p in periods))
    for row in table:
        print(f"{row[0]:6s} {row[1]:20s}" + "".join(f"{x:>12s}" for x in row[2:]))
    print(f"\n→ {a.output}  (ROA·ROE·회전율은 앞 기간이 있으면 평균 잔액 기준)")


if __name__ == "__main__":
    main()
