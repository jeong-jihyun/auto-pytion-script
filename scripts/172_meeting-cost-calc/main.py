"""회의 목록과 직급별 시간당 인건비로 회의 비용을 계산해, 비용이 큰 회의와 반복 회의의 연간 비용을 보여 주는 스크립트.

생각의 흐름:
  1) 회의는 '공짜'처럼 느껴지지만, 10명이 1시간 모이면 10명분 인건비가 듭니다.
  2) 회의마다 '참석자 직급 목록 × 직급별 시간당 비용 × 회의 시간'을 더하면 회의 비용이 됩니다.
     참석자는 '과장:2;대리:3' 처럼 직급:인원 으로 적어 개인 이름은 쓰지 않습니다.
  3) 매주 반복하는 회의는 1회 비용만 보면 작아 보이므로 '반복'(매일/매주/격주/매월)을 보고
     연간 횟수를 곱해 연간 비용도 보여 줍니다. (매일 250, 매주 52, 격주 26, 매월 12, 매분기 4회로 잡습니다)
  4) 결과는 비용 큰 순으로 정렬해 CSV로 저장하고, 화면에는 상위 몇 개와 합계를 보여 줍니다.
"""
import argparse
import csv
import os

YEARLY = {"": 1, "없음": 1, "매일": 250, "매주": 52, "격주": 26, "매월": 12, "매분기": 4}


def load_rates(path):
    """직급,시간당비용 CSV → {직급: 비용}"""
    rates = {}
    with open(path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            rates[row["직급"].strip()] = float(row["시간당비용"].replace(",", ""))
    return rates


def parse_attendees(text):
    """'과장:2;대리:3' → [('과장', 2), ('대리', 3)]"""
    out = []
    for part in text.split(";"):
        part = part.strip()
        if not part:
            continue
        if ":" in part:
            g, n = part.split(":", 1)
            out.append((g.strip(), int(n)))
        else:
            out.append((part, 1))
    return out


def main():
    ap = argparse.ArgumentParser(description="회의 비용(인건비) 계산")
    ap.add_argument("meetings", help="회의 목록 CSV (회의명,시간(분),참석자,반복)")
    ap.add_argument("--rates", required=True, help="직급별 시간당비용 CSV (직급,시간당비용)")
    ap.add_argument("--top", type=int, default=5)
    ap.add_argument("-o", "--out", default="out/meeting_cost.csv")
    args = ap.parse_args()

    rates = load_rates(args.rates)
    rows, problems = [], []
    with open(args.meetings, encoding="utf-8-sig", newline="") as f:
        for i, r in enumerate(csv.DictReader(f), start=2):
            minutes = float(r["시간(분)"])
            people, cost = 0, 0.0
            for grade, n in parse_attendees(r["참석자"]):
                if grade not in rates:
                    problems.append(f"{i}행 '{r['회의명']}': 직급 '{grade}' 비용이 rates 파일에 없음(0원으로 계산)")
                    continue
                people += n
                cost += rates[grade] * n * minutes / 60
            rep = r.get("반복", "").strip()
            if rep not in YEARLY:
                problems.append(f"{i}행 '{r['회의명']}': 반복 '{rep}'을 모름(1회로 계산)")
            yearly_n = YEARLY.get(rep, 1)
            rows.append({"회의명": r["회의명"], "시간(분)": int(minutes), "인원": people,
                         "1회비용": round(cost), "반복": rep or "없음", "연간횟수": yearly_n,
                         "연간비용": round(cost * yearly_n)})

    rows.sort(key=lambda x: -x["연간비용"])
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print(f"회의 {len(rows)}개, 1회 합계 {sum(r['1회비용'] for r in rows):,}원, 연간 합계 {sum(r['연간비용'] for r in rows):,}원")
    print(f"\n[연간 비용 상위 {args.top}]")
    for r in rows[:args.top]:
        print(f"  {r['회의명']}: {r['인원']}명 × {r['시간(분)']}분 = 1회 {r['1회비용']:,}원, {r['반복']} → 연 {r['연간비용']:,}원")
    for p in problems:
        print("  [확인] " + p)
    print(f"\n결과 → {args.out}")


if __name__ == "__main__":
    main()
