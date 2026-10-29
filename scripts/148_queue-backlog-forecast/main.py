"""배치·메시지 큐 적체량 시계열로 '늘고 있는지, 언제 다 처리될지(또는 한도에 닿을지)'를 추정하는 스크립트.

생각의 흐름:
  1) 운영 중에는 '대기 건수'를 몇 분마다 찍어 둔 기록(시각, 큐이름, 대기건수)이 있습니다.
     숫자만 보면 지금 위험한지 판단하기 어렵습니다.
  2) 큐마다 최근 N개 점(--window)에 직선을 맞춰(최소제곱 선형회귀) '분당 증가량(기울기)'을 구합니다.
  3) 기울기로 상태를 나눕니다.
       - 감소 중 : 지금 속도면 몇 분 뒤 0이 되는지(소진 예상 시각)
       - 증가 중 : --limit(한도)을 주면 몇 분 뒤 한도에 닿는지(초과 예상 시각)
       - 정체   : 기울기가 거의 0 (|기울기| < --flat)
  4) 마지막 값이 이미 한도를 넘었으면 OVER 로 바로 표시합니다.
  5) 직선이 얼마나 잘 맞는지(R²)도 같이 보여 줍니다. R²가 낮으면 예상 시각은 참고만 하라는 뜻입니다.
"""
import argparse
import csv
from collections import defaultdict
from datetime import datetime, timedelta


def parse_time(text):
    text = text.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y/%m/%d %H:%M"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass
    return None


def linreg(xs, ys):
    """기울기, 절편, R² 를 돌려줍니다."""
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0:
        return 0.0, my, 0.0
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    slope = sxy / sxx
    inter = my - slope * mx
    ss_tot = sum((y - my) ** 2 for y in ys)
    ss_res = sum((y - (slope * x + inter)) ** 2 for x, y in zip(xs, ys))
    r2 = 1 - ss_res / ss_tot if ss_tot else 1.0
    return slope, inter, r2


def main():
    p = argparse.ArgumentParser(description="큐 적체 추세·소진/초과 예상 시각")
    p.add_argument("input", help="CSV (time, queue, depth)")
    p.add_argument("-o", "--output", default="backlog_forecast.out.csv")
    p.add_argument("--window", type=int, default=12, help="최근 몇 개 점으로 추세를 볼지 (기본 12)")
    p.add_argument("--limit", type=float, default=0, help="큐 한도(이 값에 닿을 시각을 추정). 0이면 안 봄")
    p.add_argument("--flat", type=float, default=1.0, help="분당 변화가 이보다 작으면 정체로 봄 (기본 1건/분)")
    p.add_argument("--encoding", default="utf-8-sig")
    a = p.parse_args()

    series = defaultdict(list)
    bad = 0
    with open(a.input, encoding=a.encoding, newline="") as f:
        for row in csv.DictReader(f):
            t = parse_time(row.get("time", ""))
            try:
                depth = float(row.get("depth", ""))
            except ValueError:
                depth = None
            if not t or depth is None:
                bad += 1
                continue
            series[row.get("queue", "").strip()].append((t, depth))

    out = []
    for q, pts in sorted(series.items()):
        pts.sort()
        pts = pts[-a.window:]
        last_t, last_v = pts[-1]
        if len(pts) < 3:
            out.append([q, last_t.strftime("%Y-%m-%d %H:%M"), f"{last_v:g}", "", "", "자료부족", "", "점이 3개 미만"])
            continue
        t0 = pts[0][0]
        xs = [(t - t0).total_seconds() / 60 for t, _ in pts]
        ys = [v for _, v in pts]
        slope, inter, r2 = linreg(xs, ys)
        eta, note = "", ""
        if a.limit and last_v >= a.limit:
            state, note = "OVER", f"이미 한도 {a.limit:g} 이상"
        elif abs(slope) < a.flat:
            state = "정체"
        elif slope < 0:
            state = "감소"
            mins = last_v / -slope
            eta = (last_t + timedelta(minutes=mins)).strftime("%Y-%m-%d %H:%M")
            note = f"약 {mins:.0f}분 뒤 소진"
        else:
            state = "증가"
            if a.limit:
                mins = (a.limit - last_v) / slope
                eta = (last_t + timedelta(minutes=mins)).strftime("%Y-%m-%d %H:%M")
                note = f"약 {mins:.0f}분 뒤 한도 도달"
            else:
                note = "한도(--limit)를 주면 도달 시각을 계산"
        if r2 < 0.5 and eta:
            note += " (R² 낮음: 참고용)"
        out.append([q, last_t.strftime("%Y-%m-%d %H:%M"), f"{last_v:g}", f"{slope:+.1f}", f"{r2:.2f}", state, eta, note])

    with open(a.output, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["queue", "last_time", "last_depth", "slope_per_min", "r2", "state", "eta", "note"])
        w.writerows(out)

    print(f"{'큐':14s} {'마지막값':>8s} {'분당':>8s} {'R²':>5s} {'상태':6s} {'예상시각':16s} 설명")
    for r in out:
        print(f"{r[0]:14s} {r[2]:>8s} {r[3]:>8s} {r[4]:>5s} {r[5]:6s} {r[6]:16s} {r[7]}")
    if bad:
        print(f"[경고] 시각·값을 읽지 못한 줄 {bad}개는 뺐습니다")
    print(f"→ {a.output}")


if __name__ == "__main__":
    main()
