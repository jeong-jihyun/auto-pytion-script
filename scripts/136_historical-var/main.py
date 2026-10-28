"""보유 종목과 과거 종가로 포트폴리오의 '역사적 시뮬레이션 VaR'와 기대손실(ES)을 계산하는 스크립트.

생각의 흐름:
  1) VaR(Value at Risk)는 '평소 같은 시장이라면, N%의 확률로 하루 손실이 이 금액을 넘지 않는다'는 숫자입니다.
     리스크 관리 보고서·한도 관리에 기본으로 들어갑니다.
  2) 가장 이해하기 쉬운 '역사적 시뮬레이션' 방식을 씁니다.
       ① 종목별 일간 수익률 = 오늘 종가 / 어제 종가 - 1
       ② 과거 하루하루의 수익률을 '지금 보유 금액'에 적용해 그날 같았으면 손익이 얼마였을지 계산
       ③ 그 손익들을 작은 순으로 정렬해 아래 (1-신뢰수준) 지점의 손실이 VaR
       ④ 경계일을 포함해 그보다 나빴던 날들의 평균 손실이 ES(Expected Shortfall, 기대손실)
  3) 보유 기간이 N일이면 √N 을 곱해 늘리는 흔한 근사(--horizon)를 쓰되, 근사라는 점을 화면에 표시합니다.
  4) 종목별 기여도: VaR 시나리오 날(경계에 해당하는 날)에 종목별 손익이 얼마였는지 보여 줘서 '어느 종목 때문인지' 알 수 있게 합니다.
  5) 표본이 너무 적으면(기본 60일 미만) 숫자를 믿기 어렵다고 경고합니다.
"""
import argparse
import csv
import math
from pathlib import Path


def num(s):
    return float(str(s).replace(",", "").strip())


def main():
    p = argparse.ArgumentParser(description="역사적 시뮬레이션 VaR·ES 계산")
    p.add_argument("--prices", type=Path, required=True, help="종가 CSV(일자, 종목1, 종목2, ...) 날짜 오름차순")
    p.add_argument("--positions", type=Path, required=True, help="보유 CSV(종목,평가금액)")
    p.add_argument("--conf", type=float, default=0.99, help="신뢰수준(기본 0.99)")
    p.add_argument("--horizon", type=int, default=1, help="보유 기간(일, 기본 1). 1보다 크면 √N 근사")
    p.add_argument("--min-obs", type=int, default=60, help="이보다 표본이 적으면 경고(기본 60)")
    p.add_argument("-o", "--output", type=Path, default=Path("output/var_scenarios.csv"))
    a = p.parse_args()

    with a.positions.open(newline="", encoding="utf-8-sig") as fp:
        pos = {r["종목"].strip(): num(r["평가금액"]) for r in csv.DictReader(fp)}
    with a.prices.open(newline="", encoding="utf-8-sig") as fp:
        rows = list(csv.DictReader(fp))
    if not rows:
        raise SystemExit("[오류] 종가 파일이 비어 있습니다")
    missing = [k for k in pos if k not in rows[0]]
    if missing:
        raise SystemExit(f"[오류] 종가 파일에 없는 종목: {', '.join(missing)}")

    # 날짜별 시나리오 손익(종목별) 만들기. 빈 값이 있는 날은 건너뜁니다.
    scen = []
    skipped = 0
    for prev, cur in zip(rows, rows[1:]):
        try:
            pnl = {k: v * (num(cur[k]) / num(prev[k]) - 1) for k, v in pos.items()}
        except (ValueError, ZeroDivisionError):
            skipped += 1
            continue
        scen.append((cur["일자"], sum(pnl.values()), pnl))
    n = len(scen)
    if n == 0:
        raise SystemExit("[오류] 계산할 수 있는 날이 없습니다")

    scen.sort(key=lambda x: x[1])
    # 아래에서 k번째 날을 VaR 경계로 씀. 100*0.01 이 1.0000000000000009 가 되는 소수 오차를 막으려고 반올림 후 올림
    k = max(1, math.ceil(round(n * (1 - a.conf), 9)))
    var_day = scen[k - 1]
    tail = scen[:k]
    scale = math.sqrt(a.horizon)
    var = -var_day[1] * scale
    es = -sum(x[1] for x in tail) / len(tail) * scale
    total = sum(pos.values())

    print(f"보유 총액 {total:,.0f}원, 시나리오 {n}일 (빈 값 때문에 건너뜀 {skipped}일)")
    print(f"신뢰수준 {a.conf:.1%}, 보유기간 {a.horizon}일{' (√N 근사)' if a.horizon > 1 else ''}")
    print(f"  VaR : {var:,.0f}원 (총액의 {var / total:.2%})  ← 경계 시나리오 {var_day[0]}, 아래에서 {k}번째")
    print(f"  ES  : {es:,.0f}원 (경계일 포함 가장 나빴던 {len(tail)}일 평균)")
    print("  경계 시나리오 날 종목별 손익(기여도):")
    for name, v in sorted(var_day[2].items(), key=lambda x: x[1]):
        print(f"    {name}: {v * scale:,.0f}원")
    if n < a.min_obs:
        print(f"[경고] 표본 {n}일은 {a.min_obs}일보다 적습니다. 결과는 참고용으로만 보세요.")

    a.output.parent.mkdir(parents=True, exist_ok=True)
    names = list(pos)
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["순위", "일자", "포트폴리오손익"] + names)
        for i, (d, t, pnl) in enumerate(scen, start=1):
            w.writerow([i, d, round(t)] + [round(pnl[x]) for x in names])
    print(f"저장(손익 작은 순 시나리오): {a.output}")


if __name__ == "__main__":
    main()
