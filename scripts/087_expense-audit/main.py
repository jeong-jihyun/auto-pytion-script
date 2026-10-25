"""법인카드·경비 사용 내역에서 규정 위반이 의심되는 건을 골라내는 스크립트(경비 사후 점검).

생각의 흐름(감사 담당자가 눈으로 보는 순서를 그대로 코드로):
  1) 한도 초과   : 항목(식대 등)별 1회 한도를 넘었는가?           → 규칙 JSON의 limits
  2) 쪼개기 결제 : 같은 날·같은 가맹점·같은 사람이 여러 번 결제해
                   합계가 한도를 넘는가? (한도를 피하려 나눠 긁은 의심)
  3) 휴일 사용   : 토·일요일(또는 휴일 목록)에 쓴 업무 경비인가?
  4) 심야 사용   : 23시~05시처럼 늦은 시각인가?
  5) 제한 업종   : 가맹점 이름에 제한 키워드(유흥, 골프 등)가 들어 있는가?
  6) 중복 청구   : 같은 사람·같은 날·같은 금액·같은 가맹점이 두 번 이상인가?
  하나라도 걸리면 '확인 필요'로 표시하고 사유를 모두 적습니다. 판정은 사람이 합니다.
"""
import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def num(x):
    return float((x or "0").replace(",", "").strip() or 0)


def main():
    p = argparse.ArgumentParser(description="경비 사용 내역 규정 점검")
    p.add_argument("expenses", type=Path, help="경비 CSV(사용일시,사용자,항목,가맹점,금액)")
    p.add_argument("--rules", type=Path, default=Path(__file__).with_name("sample") / "rules.json")
    p.add_argument("-o", "--output", type=Path, default=Path("output/expense_flags.csv"))
    a = p.parse_args()

    rules = json.loads(a.rules.read_text(encoding="utf-8"))
    limits = rules.get("limits", {})
    holidays = set(rules.get("holidays", []))
    night_from, night_to = rules.get("night_hours", [23, 5])
    banned = rules.get("banned_keywords", [])

    with a.expenses.open(newline="", encoding="utf-8-sig") as fp:
        rows = list(csv.DictReader(fp))
    day_merchant = defaultdict(list)
    same_charge = defaultdict(list)
    for i, r in enumerate(rows):
        r["_dt"] = datetime.strptime(r["사용일시"].strip(), "%Y-%m-%d %H:%M")
        r["_amt"] = num(r["금액"])
        r["_why"] = []
        key = (r["사용자"], r["_dt"].date(), r["가맹점"].strip())
        day_merchant[key].append(i)
        same_charge[key + (r["_amt"],)].append(i)

    for r in rows:
        lim = limits.get(r["항목"].strip())
        if lim and r["_amt"] > lim:
            r["_why"].append(f"한도 초과({int(lim):,}원)")
        d = r["_dt"]
        if d.weekday() >= 5 or d.date().isoformat() in holidays:
            r["_why"].append("휴일 사용")
        if d.hour >= night_from or d.hour < night_to:
            r["_why"].append("심야 사용")
        for kw in banned:
            if kw in r["가맹점"]:
                r["_why"].append(f"제한 업종({kw})")
    for key, idx in day_merchant.items():
        if len(idx) < 2:
            continue
        total = sum(rows[i]["_amt"] for i in idx)
        lim = limits.get(rows[idx[0]]["항목"].strip())
        if lim and total > lim and all(rows[i]["_amt"] <= lim for i in idx):
            for i in idx:
                rows[i]["_why"].append(f"쪼개기 의심(같은날 {len(idx)}건 합계 {int(total):,}원)")
    for key, idx in same_charge.items():
        if len(idx) >= 2:
            for i in idx[1:]:
                rows[i]["_why"].append("중복 청구 의심")

    fields = [k for k in rows[0].keys() if not k.startswith("_")] if rows else []
    flagged = [r for r in rows if r["_why"]]
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(fields + ["판정", "사유"])
        for r in rows:
            w.writerow([r[k] for k in fields] + ["확인 필요" if r["_why"] else "정상", " / ".join(r["_why"])])
    print(f"경비 {len(rows)}건 중 확인 필요 {len(flagged)}건 → {a.output}")
    for r in flagged:
        print(f"  - {r['사용일시']} {r['사용자']} {r['가맹점']} {int(r['_amt']):,}원: {' / '.join(r['_why'])}")


if __name__ == "__main__":
    main()
