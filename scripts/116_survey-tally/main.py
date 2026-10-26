"""설문 응답 CSV를 문항 종류별로 집계해 결과표(CSV)와 요약(마크다운)을 만드는 스크립트.

생각의 흐름:
  1) 설문 도구에서 내려받은 응답 CSV는 한 줄이 응답자 1명, 한 열이 문항 1개입니다.
  2) 문항은 세 종류로 나눠 셉니다.
     - 단일선택(--single): 보기별 응답 수와 비율
     - 복수선택(--multi): 한 칸에 '보기A;보기B'처럼 여러 개 → 나눠서 셈. 비율은 '응답자 대비'
     - 점수(--scale): 1~5점 같은 숫자 → 평균·응답 수·점수별 분포
  3) 빈칸은 '무응답'으로 따로 셉니다.
  4) 결과를 한 CSV(문항,종류,보기,응답수,비율)와 읽기 쉬운 마크다운 요약으로 저장합니다.
"""
import argparse
import csv
from collections import Counter
from pathlib import Path


def pct(n, d):
    return round(n / d * 100, 1) if d else 0


def main():
    p = argparse.ArgumentParser(description="설문 응답 집계")
    p.add_argument("responses", type=Path, help="응답 CSV")
    p.add_argument("--single", nargs="*", default=[], help="단일선택 문항 열 이름들")
    p.add_argument("--multi", nargs="*", default=[], help="복수선택 문항 열 이름들")
    p.add_argument("--scale", nargs="*", default=[], help="점수 문항 열 이름들")
    p.add_argument("--sep", default=";", help="복수선택 구분자(기본 ;)")
    p.add_argument("-o", "--outdir", type=Path, default=Path("output"))
    a = p.parse_args()

    with a.responses.open(newline="", encoding="utf-8-sig") as fp:
        data = list(csv.DictReader(fp))
    n = len(data)
    rows, md = [], [f"# 설문 집계 결과\n\n전체 응답자: {n}명\n"]

    for col in a.single:
        c = Counter((r.get(col) or "").strip() or "무응답" for r in data)
        md.append(f"## {col} (단일선택)\n\n| 보기 | 응답수 | 비율 |\n|---|---|---|")
        for k, v in c.most_common():
            rows.append([col, "단일선택", k, v, pct(v, n)])
            md.append(f"| {k} | {v} | {pct(v, n)}% |")
        md.append("")

    for col in a.multi:
        c, blank = Counter(), 0
        for r in data:
            picks = [x.strip() for x in (r.get(col) or "").split(a.sep) if x.strip()]
            if not picks:
                blank += 1
            c.update(set(picks))  # 한 사람이 같은 보기를 두 번 적어도 1번만 셈
        md.append(f"## {col} (복수선택, 비율은 응답자 대비라 합이 100%를 넘을 수 있음)\n\n| 보기 | 응답수 | 비율 |\n|---|---|---|")
        for k, v in c.most_common() + ([("무응답", blank)] if blank else []):
            rows.append([col, "복수선택", k, v, pct(v, n)])
            md.append(f"| {k} | {v} | {pct(v, n)}% |")
        md.append("")

    for col in a.scale:
        vals, blank = [], 0
        for r in data:
            s = (r.get(col) or "").strip()
            try:
                vals.append(float(s))
            except ValueError:
                blank += 1
        avg = round(sum(vals) / len(vals), 2) if vals else 0
        dist = Counter(vals)
        md.append(f"## {col} (점수)\n\n평균 **{avg}점** (응답 {len(vals)}명, 무응답·숫자 아님 {blank}명)\n\n| 점수 | 응답수 | 비율 |\n|---|---|---|")
        rows.append([col, "점수평균", "평균", avg, ""])
        for k in sorted(dist):
            rows.append([col, "점수", f"{k:g}", dist[k], pct(dist[k], len(vals))])
            md.append(f"| {k:g} | {dist[k]} | {pct(dist[k], len(vals))}% |")
        md.append("")

    a.outdir.mkdir(parents=True, exist_ok=True)
    with (a.outdir / "survey_tally.csv").open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["문항", "종류", "보기", "응답수", "비율%"])
        w.writerows(rows)
    (a.outdir / "survey_summary.md").write_text("\n".join(md), encoding="utf-8")
    print(f"응답자 {n}명, 문항 {len(a.single) + len(a.multi) + len(a.scale)}개 집계 → {a.outdir}")


if __name__ == "__main__":
    main()
