"""월별 실적 CSV로 전월 대비(MoM)·전년 동월 대비(YoY) 증감률과 누적(YTD)을 계산하는 스크립트.

생각의 흐름:
  1) 월간 보고서에는 늘 "지난달보다 몇 % 늘었나", "작년 같은 달보다는?", "올해 누적은?"이 들어갑니다.
     엑셀에서 매달 수식을 끌어다 쓰다 보면 행이 밀려 틀리기 쉽습니다.
  2) 입력은 '월(YYYY-MM), 항목(예: 지점·제품), 값' 형태의 긴 표로 받습니다.
  3) 항목별로 월을 정렬하고
       - MoM = (이번달 - 지난달) / 지난달
       - YoY = (이번달 - 작년같은달) / 작년같은달
       - YTD = 그해 1월부터 이번달까지 합계
       - YTD YoY = 올해·작년 모두 자료가 있는 달끼리만 더해 비교
     를 계산합니다. 비교 대상 달이 없거나 0이면 빈칸으로 둡니다(0으로 나누기 방지).
  4) 달이 빠져 있으면(예: 3월 자료 없음) '지난달'은 바로 앞 달력 월로만 봅니다. 빠진 달을 건너뛰어 비교하지 않습니다.
  5) --month 를 주면 그 달만 요약해서 화면에 증감률 순위로 보여 줍니다.
"""
import argparse
import csv
from collections import defaultdict


def prev_month(ym, back=1):
    y, m = int(ym[:4]), int(ym[5:7])
    m -= back
    while m <= 0:
        m += 12
        y -= 1
    return f"{y:04d}-{m:02d}"


def rate(cur, base):
    if base in (None, 0) or cur is None:
        return None
    return (cur - base) / abs(base)


def fmt(r):
    return "" if r is None else f"{r*100:.1f}%"


def n(v):
    """숫자를 1234567 또는 1234.5 처럼 지수 표기 없이 씁니다."""
    if v is None:
        return ""
    return f"{v:.0f}" if float(v).is_integer() else f"{v:.2f}"


def main():
    p = argparse.ArgumentParser(description="전월·전년 동월 대비 증감률 계산")
    p.add_argument("input", help="월별 실적 CSV (월, 항목, 값)")
    p.add_argument("-o", "--output", default="growth.out.csv")
    p.add_argument("--col-month", default="월")
    p.add_argument("--col-item", default="항목")
    p.add_argument("--col-value", default="값")
    p.add_argument("--month", help="화면에 요약할 달 (예: 2026-09)")
    p.add_argument("--encoding", default="utf-8-sig")
    a = p.parse_args()

    data = defaultdict(dict)  # 항목 → {월: 값}
    with open(a.input, encoding=a.encoding, newline="") as f:
        for row in csv.DictReader(f):
            ym = row[a.col_month].strip().replace("/", "-").replace(".", "-")[:7]
            if len(ym) != 7 or ym[4] != "-":
                print(f"[경고] 월 형식 오류로 건너뜀: {row[a.col_month]}")
                continue
            item = row[a.col_item].strip()
            val = float(row[a.col_value].replace(",", "") or 0)
            data[item][ym] = data[item].get(ym, 0) + val  # 같은 달 여러 줄이면 합칩니다

    out = []
    for item in sorted(data):
        series = data[item]
        for ym in sorted(series):
            cur = series[ym]
            ytd = sum(v for k, v in series.items() if k[:4] == ym[:4] and k <= ym)
            ly = prev_month(ym, 12)
            # YTD YoY 는 '올해와 작년 모두 자료가 있는 달'끼리만 더해서 비교합니다(빠진 달 때문에 왜곡되지 않게).
            pairs = [(v, series[prev_month(k, 12)]) for k, v in series.items()
                     if k[:4] == ym[:4] and k <= ym and prev_month(k, 12) in series]
            ytd_ly = (sum(p[0] for p in pairs), sum(p[1] for p in pairs)) if pairs else None
            out.append({
                "월": ym, "항목": item, "값": cur,
                "전월": series.get(prev_month(ym)), "MoM": rate(cur, series.get(prev_month(ym))),
                "전년동월": series.get(ly), "YoY": rate(cur, series.get(ly)),
                "YTD": ytd, "YTD_YoY": rate(*ytd_ly) if ytd_ly else None,
            })

    with open(a.output, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["월", "항목", "값", "전월", "MoM", "전년동월", "YoY", "YTD", "YTD_YoY"])
        for r in out:
            w.writerow([r["월"], r["항목"], n(r["값"]), n(r["전월"]), fmt(r["MoM"]),
                        n(r["전년동월"]), fmt(r["YoY"]), n(r["YTD"]), fmt(r["YTD_YoY"])])
    print(f"항목 {len(data)}개, {len(out)}줄 계산 → {a.output}")

    if a.month:
        rows = [r for r in out if r["월"] == a.month]
        if not rows:
            print(f"[안내] {a.month} 자료가 없습니다.")
            return
        rows.sort(key=lambda r: -(r["YoY"] if r["YoY"] is not None else -9e9))
        print(f"\n[{a.month} 요약] YoY 높은 순")
        print(f"{'항목':10s} {'값':>12s} {'MoM':>8s} {'YoY':>8s} {'YTD':>14s} {'YTD YoY':>8s}")
        for r in rows:
            print(f"{r['항목']:10s} {r['값']:12,.0f} {fmt(r['MoM']):>8s} {fmt(r['YoY']):>8s} {r['YTD']:14,.0f} {fmt(r['YTD_YoY']):>8s}")


if __name__ == "__main__":
    main()
