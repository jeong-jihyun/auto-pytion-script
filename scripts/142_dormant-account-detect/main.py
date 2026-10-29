"""계좌 목록과 거래 내역으로 '휴면 계좌 후보'를 뽑는 스크립트.

생각의 흐름:
  1) 금융회사는 일정 기간(예: 1년, 5년) 거래가 없는 계좌를 휴면으로 분류하고, 그 전에 고객에게 안내해야 합니다.
  2) 계좌 마스터(계좌번호, 고객명, 개설일, 잔액)와 거래 내역(계좌번호, 거래일)을 받아
     계좌별 '마지막 거래일'을 구합니다. 거래가 한 번도 없으면 개설일을 기준으로 씁니다.
  3) 기준일(--as-of)에서 며칠 지났는지 계산해 세 단계로 나눕니다.
       - DORMANT : --dormant-days 이상 거래 없음 (휴면 대상)
       - NOTICE  : 휴면까지 --notice-days 이내로 남음 (사전 안내 대상)
       - ACTIVE  : 그 외 (결과 파일에는 넣지 않음)
  4) 잔액이 --min-balance 미만이면 '소액'으로 따로 표시해 일괄 처리 여부를 판단하게 합니다.
  5) 해지 계좌(상태 열이 '해지')는 건너뜁니다.
"""
import argparse
import csv
from datetime import datetime, timedelta


def to_date(text):
    text = (text or "").strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    return None


def main():
    p = argparse.ArgumentParser(description="휴면 계좌 후보 추출")
    p.add_argument("accounts", help="계좌 마스터 CSV (계좌번호, 고객명, 개설일, 잔액, 상태)")
    p.add_argument("transactions", help="거래 내역 CSV (계좌번호, 거래일)")
    p.add_argument("-o", "--output", default="dormant_candidates.out.csv")
    p.add_argument("--as-of", default=None, help="기준일 (기본: 오늘)")
    p.add_argument("--dormant-days", type=int, default=365, help="이 일수 이상 거래 없으면 휴면 (기본 365)")
    p.add_argument("--notice-days", type=int, default=30, help="휴면까지 남은 일수가 이 이하이면 사전 안내 (기본 30)")
    p.add_argument("--min-balance", type=float, default=10000, help="소액 기준 잔액 (기본 10,000)")
    p.add_argument("--encoding", default="utf-8-sig")
    a = p.parse_args()

    as_of = to_date(a.as_of) if a.as_of else datetime.now().date()
    if not as_of:
        raise SystemExit("[오류] --as-of 형식이 틀렸습니다. 예: 2026-10-29")

    # 1단계: 계좌별 마지막 거래일 구하기 (기준일보다 뒤 거래는 무시)
    last = {}
    skipped = 0
    with open(a.transactions, encoding=a.encoding, newline="") as f:
        for row in csv.DictReader(f):
            d = to_date(row.get("거래일"))
            acc = (row.get("계좌번호") or "").strip()
            if not d or not acc or d > as_of:
                skipped += 1
                continue
            if acc not in last or d > last[acc]:
                last[acc] = d

    out = []
    stat = {"DORMANT": 0, "NOTICE": 0, "ACTIVE": 0, "CLOSED": 0}
    with open(a.accounts, encoding=a.encoding, newline="") as f:
        for row in csv.DictReader(f):
            acc = row["계좌번호"].strip()
            if (row.get("상태") or "").strip() == "해지":
                stat["CLOSED"] += 1
                continue
            base = last.get(acc) or to_date(row.get("개설일"))
            if not base:
                print(f"[경고] {acc}: 거래도 개설일도 없어 건너뜁니다")
                continue
            idle = (as_of - base).days
            left = a.dormant_days - idle
            if left <= 0:
                level = "DORMANT"
            elif left <= a.notice_days:
                level = "NOTICE"
            else:
                stat["ACTIVE"] += 1
                continue
            stat[level] += 1
            bal = float((row.get("잔액") or "0").replace(",", ""))
            out.append({
                "계좌번호": acc,
                "고객명": row.get("고객명", ""),
                "마지막거래일": base.isoformat(),
                "기준": "거래" if acc in last else "개설일",
                "무거래일수": idle,
                "휴면예정일": (base + timedelta(days=a.dormant_days)).isoformat(),
                "구분": level,
                "잔액": f"{bal:.0f}",
                "소액": "Y" if bal < a.min_balance else "",
            })

    out.sort(key=lambda r: (r["구분"] != "DORMANT", -r["무거래일수"]))
    fields = ["계좌번호", "고객명", "마지막거래일", "기준", "무거래일수", "휴면예정일", "구분", "잔액", "소액"]
    with open(a.output, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(out)

    print(f"기준일 {as_of} / 휴면 기준 {a.dormant_days}일 / 사전안내 {a.notice_days}일 전")
    print(f"  휴면 대상 {stat['DORMANT']}건, 사전 안내 {stat['NOTICE']}건, 정상 {stat['ACTIVE']}건, 해지 제외 {stat['CLOSED']}건")
    if skipped:
        print(f"  (거래 내역 중 날짜 오류·기준일 이후 {skipped}줄은 빼고 계산)")
    print(f"결과 → {a.output}")


if __name__ == "__main__":
    main()
