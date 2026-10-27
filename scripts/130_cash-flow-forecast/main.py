"""입금·출금 예정표로 날짜별 예상 잔액을 계산하고, 돈이 모자라는 날을 미리 알려 주는 스크립트.

생각의 흐름:
  1) 자금 담당자는 '다음 몇 주 동안 통장 잔액이 바닥나는 날이 있나?'를 미리 알아야 합니다.
  2) 오늘 잔액에서 시작해, 날짜순으로 그날의 입금은 더하고 출금은 뺍니다.
  3) 입금은 '확정'(계약·청구 완료)과 '예상'(들어올 것 같음)이 섞여 있어서 두 가지 잔액을 같이 봅니다.
       기본 잔액   : 모든 입금 + 모든 출금 반영
       보수적 잔액 : 확정 입금만 + 모든 출금 반영 (예상 입금이 안 들어와도 버틸 수 있나?)
     출금은 늦출 수 없다고 보고 언제나 모두 반영합니다.
  4) 잔액이 최소 유지 잔액(--min) 아래로 내려가는 날을 '부족'/'주의'로 표시하고,
     가장 낮은 잔액과 그 날짜를 알려 줍니다.
  5) 금액은 원 단위 정수로 계산합니다.
"""
import argparse
import csv
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path


def won(s):
    return int(str(s).replace(",", "").strip() or 0)


def main():
    p = argparse.ArgumentParser(description="자금 수지 예측(일별 예상 잔액)")
    p.add_argument("plan", type=Path, help="CSV(예정일,구분(입금/출금),거래처,금액,확정여부(확정/예상))")
    p.add_argument("--start-balance", required=True, help="시작일 아침 잔액(원)")
    p.add_argument("--start", required=True, help="시작일 YYYY-MM-DD")
    p.add_argument("--days", type=int, default=30, help="며칠 앞까지 볼지(기본 30)")
    p.add_argument("--min", default="0", help="최소 유지 잔액(원, 기본 0)")
    p.add_argument("-o", "--output", type=Path, default=Path("output/cash_forecast.csv"))
    a = p.parse_args()

    start = datetime.strptime(a.start, "%Y-%m-%d").date()
    end = start + timedelta(days=a.days - 1)
    min_bal = won(a.min)
    inflow, inflow_sure, outflow = defaultdict(int), defaultdict(int), defaultdict(int)
    memo = defaultdict(list)
    outside = 0
    with a.plan.open(newline="", encoding="utf-8-sig") as fp:
        for r in csv.DictReader(fp):
            day = datetime.strptime(r["예정일"].strip(), "%Y-%m-%d").date()
            if not start <= day <= end:
                outside += 1
                continue
            amt, kind = won(r["금액"]), r["구분"].strip()
            sure = r.get("확정여부", "확정").strip() != "예상"
            if kind == "입금":
                inflow[day] += amt
                if sure:
                    inflow_sure[day] += amt
                memo[day].append(f"+{r['거래처'].strip()}{'' if sure else '(예상)'}")
            elif kind == "출금":
                outflow[day] += amt
                memo[day].append(f"-{r['거래처'].strip()}")
            else:
                print(f"[건너뜀] 구분은 입금/출금만: {r}")

    bal = bal_safe = won(a.start_balance)
    rows, low, low_safe = [], None, None
    for i in range(a.days):
        day = start + timedelta(days=i)
        bal += inflow[day] - outflow[day]
        bal_safe += inflow_sure[day] - outflow[day]
        if bal < min_bal:
            flag = "부족"
        elif bal_safe < min_bal:
            flag = "주의(예상입금 안 오면 부족)"
        else:
            flag = ""
        rows.append([day, "월화수목금토일"[day.weekday()], inflow[day], outflow[day], bal, bal_safe, flag,
                     " ".join(memo[day])])
        if low is None or bal < low[1]:
            low = (day, bal)
        if low_safe is None or bal_safe < low_safe[1]:
            low_safe = (day, bal_safe)

    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["일자", "요일", "입금합", "출금합", "예상잔액", "보수적잔액", "경고", "내역"])
        w.writerows(rows)

    print(f"기간 {start} ~ {end} | 시작 잔액 {won(a.start_balance):,}원 | 최소 유지 {min_bal:,}원")
    for r in rows:
        if r[2] or r[3]:
            print(f"  {r[0]}({r[1]}) 입금 {r[2]:>12,} 출금 {r[3]:>12,} → 잔액 {r[4]:>13,} / 보수적 {r[5]:>13,} {r[6]}")
    print(f"가장 낮은 잔액: {low[1]:,}원({low[0]}), 보수적으로는 {low_safe[1]:,}원({low_safe[0]})")
    short = sum(1 for r in rows if r[6] == "부족")
    caution = sum(1 for r in rows if r[6].startswith("주의"))
    print(f"경고 일수: 부족 {short}일, 주의 {caution}일 (날짜별 내용은 CSV의 '경고' 열)")
    weekend = [r for r in rows if r[1] in "토일" and (r[2] or r[3])]
    if weekend:
        print(f"※ 주말에 잡힌 예정 {len(weekend)}일 - 실제 이체일을 확인하세요(113 휴일 날짜 조정 스크립트 참고).")
    if outside:
        print(f"※ 기간 밖이라 뺀 예정 {outside}건")
    print(f"-> {a.output}")


if __name__ == "__main__":
    main()
