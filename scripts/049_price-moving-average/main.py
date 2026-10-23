"""일별 종가 CSV에서 이동평균, 일간 수익률, 최대 낙폭(MDD)을 계산하는 스크립트.

입력 CSV 열: 날짜, 종가 (열 이름은 --date-col, --price-col 로 바꿀 수 있습니다)
출력 CSV 열: 날짜, 종가, 일간수익률(%), MA5, MA20 (기간은 --windows 로 바꿉니다)
화면에는 최대 낙폭(고점 대비 가장 크게 떨어진 비율)과 기간 수익률 요약도 보여줍니다.
교육·업무 점검용 계산이며 투자 판단 자료가 아닙니다.
"""
import argparse
import csv
import sys
from pathlib import Path


def moving_average(values, n):
    """각 위치의 최근 n개 평균. 아직 n개가 안 쌓였으면 빈 칸(None)."""
    out = []
    for i in range(len(values)):
        out.append(None if i + 1 < n else sum(values[i + 1 - n:i + 1]) / n)
    return out


def main():
    p = argparse.ArgumentParser(description="이동평균·수익률·MDD 계산")
    p.add_argument("input", type=Path)
    p.add_argument("--date-col", default="날짜")
    p.add_argument("--price-col", default="종가")
    p.add_argument("--windows", default="5,20", help="이동평균 기간(쉼표 구분)")
    p.add_argument("-o", "--output", type=Path, default=Path("output/ma.csv"))
    a = p.parse_args()

    dates, prices = [], []
    with a.input.open(newline="", encoding="utf-8-sig") as fp:
        r = csv.DictReader(fp)
        for col in (a.date_col, a.price_col):
            if col not in (r.fieldnames or []):
                print(f"[오류] 없는 열: {col} (있는 열: {r.fieldnames})")
                sys.exit(1)
        for row in r:
            try:
                prices.append(float(row[a.price_col].replace(",", "")))
                dates.append(row[a.date_col])
            except ValueError:
                print(f"[건너뜀] 숫자가 아닌 종가: {row}")
    if len(prices) < 2:
        print("[오류] 계산할 데이터가 2행 이상 필요합니다.")
        sys.exit(1)
    # 날짜 순서로 정렬(YYYY-MM-DD 글자 순서 = 날짜 순서)
    pairs = sorted(zip(dates, prices))
    dates, prices = [x[0] for x in pairs], [x[1] for x in pairs]

    wins = [int(w) for w in a.windows.split(",") if w.strip()]
    mas = {w: moving_average(prices, w) for w in wins}
    rets = [None] + [(prices[i] / prices[i - 1] - 1) * 100 for i in range(1, len(prices))]

    # 최대 낙폭: 지금까지의 최고가 대비 얼마나 떨어졌는지의 최대값
    peak, mdd, mdd_date = prices[0], 0.0, dates[0]
    for d, pr in zip(dates, prices):
        peak = max(peak, pr)
        dd = (pr / peak - 1) * 100
        if dd < mdd:
            mdd, mdd_date = dd, d

    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["날짜", "종가", "일간수익률(%)"] + [f"MA{n}" for n in wins])
        for i, d in enumerate(dates):
            w.writerow([d, prices[i], "" if rets[i] is None else f"{rets[i]:.2f}"]
                       + ["" if mas[n][i] is None else f"{mas[n][i]:.2f}" for n in wins])
    total = (prices[-1] / prices[0] - 1) * 100
    print(f"{len(prices)}일 데이터 ({dates[0]} ~ {dates[-1]}) -> {a.output}")
    print(f"기간 수익률 {total:.2f}%  /  최대 낙폭 {mdd:.2f}% ({mdd_date})")


if __name__ == "__main__":
    main()
