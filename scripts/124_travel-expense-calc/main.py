"""출장 내역과 여비 규정으로 사람별 출장비(일비·식비·숙박비·교통비)를 계산하는 스크립트.

생각의 흐름:
  1) 출장비 정산은 '며칠, 몇 박, 어느 지역'만 알면 규정대로 계산되는데, 손으로 하면 일수·한도를 자주 틀립니다.
  2) 일수 = 종료일 - 시작일 + 1 (당일 출장은 1일), 박수 = 일수 - 1 로 셉니다.
  3) 규정(JSON)에서 지역 등급별 일비·식비(하루), 숙박 한도(1박)를 가져옵니다.
       일비 = 일수 × 하루 일비,  식비 = 일수 × 하루 식비
       숙박 인정액 = min(실제 숙박비, 박수 × 1박 한도)  → 넘는 돈은 '숙박 초과'(본인 부담)로 따로 표시
       교통비는 실비 그대로
  4) 출장 건별 계산표와 사람별 합계표를 만듭니다. 금액은 원 단위 정수로 계산해 반올림 오차를 없앱니다.
"""
import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def won(s):
    s = str(s or "0").replace(",", "").strip()
    return int(s) if s else 0


def main():
    p = argparse.ArgumentParser(description="출장비 계산(일비·식비·숙박 한도·교통비)")
    p.add_argument("trips", type=Path, help="CSV(이름,부서,지역등급,시작일,종료일,숙박비,교통비)")
    p.add_argument("--rules", type=Path, required=True, help="여비 규정 JSON")
    p.add_argument("-o", "--outdir", type=Path, default=Path("output"))
    a = p.parse_args()

    rules = json.loads(a.rules.read_text(encoding="utf-8"))
    detail, errors = [], []
    per_person = defaultdict(lambda: [0, 0, 0, 0, 0, 0, 0])  # 건수,일수,일비,식비,숙박,교통,합계
    with a.trips.open(newline="", encoding="utf-8-sig") as fp:
        for i, r in enumerate(csv.DictReader(fp), start=2):
            name, grade = r["이름"].strip(), r["지역등급"].strip()
            if grade not in rules:
                errors.append(f"{i}행 {name}: 규정에 없는 지역등급 '{grade}'")
                continue
            s = datetime.strptime(r["시작일"].strip(), "%Y-%m-%d").date()
            e = datetime.strptime(r["종료일"].strip(), "%Y-%m-%d").date()
            if e < s:
                errors.append(f"{i}행 {name}: 종료일이 시작일보다 빠름")
                continue
            days = (e - s).days + 1
            nights = days - 1
            rule = rules[grade]
            per_diem = days * rule["일비"]
            meal = days * rule["식비"]
            lodging_real = won(r["숙박비"])
            lodging_cap = nights * rule["숙박한도"]
            lodging = min(lodging_real, lodging_cap)
            over = lodging_real - lodging
            transport = won(r["교통비"])
            total = per_diem + meal + lodging + transport
            note = f"숙박 한도 초과 {over:,}원 본인 부담" if over else ""
            if nights == 0 and lodging_real:
                note = "당일 출장인데 숙박비 있음(확인 필요)"
            detail.append([name, r["부서"].strip(), grade, s, e, days, nights,
                           per_diem, meal, lodging_real, lodging, transport, total, note])
            pp = per_person[(name, r["부서"].strip())]
            for k, v in enumerate([1, days, per_diem, meal, lodging, transport, total]):
                pp[k] += v

    a.outdir.mkdir(parents=True, exist_ok=True)
    with (a.outdir / "trip_detail.csv").open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["이름", "부서", "지역등급", "시작일", "종료일", "일수", "박수", "일비", "식비",
                    "숙박비실비", "숙박인정", "교통비", "지급합계", "메모"])
        w.writerows(detail)
    with (a.outdir / "person_total.csv").open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["이름", "부서", "출장건수", "총일수", "일비", "식비", "숙박", "교통비", "지급합계"])
        for (name, dept), v in sorted(per_person.items()):
            w.writerow([name, dept] + v)

    for (name, dept), v in sorted(per_person.items()):
        print(f"{name}({dept}) 출장 {v[0]}건 {v[1]}일 → 지급 {v[6]:,}원")
    for d in detail:
        if d[13]:
            print(f"  [메모] {d[0]} {d[3]}~{d[4]}: {d[13]}")
    for msg in errors:
        print(f"  [오류] {msg}")
    print(f"총 지급액 {sum(d[12] for d in detail):,}원 -> {a.outdir}/trip_detail.csv, person_total.csv")


if __name__ == "__main__":
    main()
