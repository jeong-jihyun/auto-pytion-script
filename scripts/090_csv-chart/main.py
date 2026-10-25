"""CSV 표를 읽어 막대·선·가로막대 그래프 PNG를 만드는 스크립트(보고서 붙임용).

생각의 흐름:
  1) x축 열 하나와 y축 열 여러 개를 고릅니다. 같은 x 값이 여러 줄이면 합계를 냅니다.
     (예: 일자별 거래 → 월별 합계 막대)
  2) 숫자 열의 쉼표(1,234)는 지우고 숫자로 바꿉니다. 숫자가 아니면 그 칸은 0이 아니라 '건너뜀'으로 셉니다.
  3) 한글 제목·축이 깨지지 않도록 설치된 한글 글꼴을 찾아 씁니다.
  4) 막대 위에 값(천 단위 쉼표)을 적어, 그림만 봐도 숫자를 읽을 수 있게 합니다.
  5) 화면 없이(서버·배치에서도) 그릴 수 있게 Agg 방식으로 PNG 파일만 저장합니다.
"""
import argparse
import csv
from collections import OrderedDict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

KOREAN_FONTS = ["Malgun Gothic", "AppleGothic", "Apple SD Gothic Neo", "NanumGothic",
                "Noto Sans CJK KR", "Noto Sans CJK JP", "Noto Sans CJK SC"]


def use_korean_font():
    names = {f.name for f in font_manager.fontManager.ttflist}
    for n in KOREAN_FONTS:
        if n in names:
            plt.rcParams["font.family"] = n
            plt.rcParams["axes.unicode_minus"] = False
            return n
    print("  ! 한글 글꼴을 찾지 못했습니다. 한글이 네모로 보일 수 있습니다.")
    return None


def main():
    p = argparse.ArgumentParser(description="CSV로 그래프 PNG 만들기")
    p.add_argument("csv", type=Path)
    p.add_argument("--x", required=True, help="x축 열 이름(예: 월)")
    p.add_argument("--y", required=True, help="y축 열 이름, 여러 개면 쉼표(예: 매출,비용)")
    p.add_argument("--kind", choices=["bar", "line", "barh"], default="bar")
    p.add_argument("--title", default="")
    p.add_argument("--unit", default="", help="y축 단위 글자(예: 원)")
    p.add_argument("--month", action="store_true", help="x 값이 날짜면 YYYY-MM 으로 묶기")
    p.add_argument("-o", "--output", type=Path, default=Path("output/chart.png"))
    a = p.parse_args()

    ys = [y.strip() for y in a.y.split(",") if y.strip()]
    data, skipped = OrderedDict(), 0
    with a.csv.open(newline="", encoding="utf-8-sig") as fp:
        reader = csv.DictReader(fp)
        miss = [c for c in [a.x] + ys if c not in (reader.fieldnames or [])]
        if miss:
            raise SystemExit(f"열을 찾을 수 없습니다: {miss} / 있는 열: {reader.fieldnames}")
        for r in reader:
            key = r[a.x].strip()
            if a.month:
                key = key.replace(".", "-").replace("/", "-")[:7]
            slot = data.setdefault(key, [0.0] * len(ys))
            for i, y in enumerate(ys):
                try:
                    slot[i] += float((r[y] or "").replace(",", ""))
                except ValueError:
                    skipped += 1
    if a.month:
        data = OrderedDict(sorted(data.items()))

    font = use_korean_font()
    labels = list(data.keys())
    fig, ax = plt.subplots(figsize=(max(6, len(labels) * 0.8), 4.5), dpi=120)
    n = len(ys)
    width = 0.8 / n
    for i, y in enumerate(ys):
        vals = [data[k][i] for k in labels]
        if a.kind == "line":
            ax.plot(labels, vals, marker="o", label=y)
        else:
            pos = [j + (i - (n - 1) / 2) * width for j in range(len(labels))]
            bars = (ax.barh if a.kind == "barh" else ax.bar)(pos, vals, width, label=y)
            ax.bar_label(bars, labels=[f"{v:,.0f}" for v in vals], fontsize=8, padding=2)
    if a.kind != "line":
        (ax.set_yticks if a.kind == "barh" else ax.set_xticks)(range(len(labels)), labels)
    fmt = FuncFormatter(lambda v, _: f"{v:,.0f}")
    (ax.xaxis if a.kind == "barh" else ax.yaxis).set_major_formatter(fmt)
    ax.set_title(a.title or f"{', '.join(ys)} ({a.x}별)")
    if a.unit:
        (ax.set_xlabel if a.kind == "barh" else ax.set_ylabel)(a.unit)
    if n > 1:
        ax.legend()
    ax.grid(axis="x" if a.kind == "barh" else "y", alpha=0.3)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    a.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(a.output)
    print(f"{a.x} {len(labels)}개 × {', '.join(ys)} → {a.output} (글꼴: {font or '기본'})")
    if skipped:
        print(f"  ! 숫자가 아니라 건너뛴 칸 {skipped}개")


if __name__ == "__main__":
    main()
