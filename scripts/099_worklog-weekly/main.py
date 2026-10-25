"""업무일지 CSV를 주차별·프로젝트별 시간 합계와 마크다운 주간 보고서로 만드는 스크립트.

생각의 흐름:
  1) 업무일지(일자,프로젝트,내용,시간)를 읽고 일자로 ISO 주차(예: 2026-W43)를 구합니다.
  2) 주차 x 프로젝트별 시간을 더합니다.
  3) 주차마다 프로젝트별 시간과 주요 내용(최대 3줄)을 마크다운으로 적습니다.
  4) 날짜나 시간이 잘못된 줄은 건너뛰고 몇 줄인지 알려 줍니다.
"""
import argparse
import csv
from collections import defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description="업무일지 주간 요약")
    p.add_argument("--input", required=True, help="CSV(일자,프로젝트,내용,시간)")
    p.add_argument("--out", default="output/주간보고.md")
    a = p.parse_args()

    hours = defaultdict(lambda: defaultdict(Decimal))
    notes = defaultdict(lambda: defaultdict(list))
    bad = 0
    with open(a.input, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            try:
                d = datetime.strptime(r["일자"].strip(), "%Y-%m-%d")
                h = Decimal(r["시간"].strip())
            except (ValueError, InvalidOperation):
                bad += 1
                continue
            y, w, _ = d.isocalendar()
            key = f"{y}-W{w:02d}"
            hours[key][r["프로젝트"]] += h
            notes[key][r["프로젝트"]].append(r["내용"].strip())

    lines = ["# 주간 업무 보고", ""]
    for week in sorted(hours):
        total = sum(hours[week].values())
        lines += [f"## {week} (총 {total}시간)", "", "| 프로젝트 | 시간 | 주요 내용 |", "|---|---|---|"]
        for proj, h in sorted(hours[week].items(), key=lambda x: -x[1]):
            lines.append(f"| {proj} | {h} | {'; '.join(notes[week][proj][:3])} |")
        lines.append("")
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"완료: {len(hours)}개 주차 -> {out} (잘못된 줄 {bad}개 건너뜀)")


if __name__ == "__main__":
    main()
