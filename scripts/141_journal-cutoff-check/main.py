"""전표(분개) CSV에서 '기간 귀속(컷오프)'이 의심스러운 건을 찾는 스크립트.

생각의 흐름:
  1) 월말·분기말 마감 때 가장 흔한 실수는 '거래가 일어난 달'과 '장부에 올린 달(전기일)'이 다른 경우입니다.
     예: 9월 30일 거래를 10월 2일 전기 → 9월 비용이 10월로 넘어가 손익이 틀어집니다.
  2) 그래서 전표마다 다음을 봅니다.
       - MONTH_DIFF : 거래일(증빙일)과 전기일의 '연-월'이 다름
       - AFTER_CLOSE: 마감일(--close-date) 이후에 입력(입력일)되었는데 전기일은 마감된 달 안
       - WEEKEND    : 전기일이 토·일 (설정에 따라 확인용)
       - BACKDATED  : 입력일보다 전기일이 --backdate-days 일 넘게 과거 (소급 전기)
  3) 같은 전표번호의 여러 줄은 한 번만 보고 금액은 차변 합계로 보여 줍니다.
  4) 결과는 CSV로 저장하고, 화면에는 사유별 건수와 금액을 요약합니다.
"""
import argparse
import csv
from collections import OrderedDict, defaultdict
from datetime import date, datetime


def to_date(text):
    text = (text or "").strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    return None


def to_num(text):
    try:
        return float(str(text).replace(",", "").strip() or 0)
    except ValueError:
        return 0.0


def main():
    p = argparse.ArgumentParser(description="전표 기간 귀속(컷오프) 점검")
    p.add_argument("input", help="전표 CSV (전표번호, 거래일, 전기일, 입력일, 차변 열 필요)")
    p.add_argument("-o", "--output", default="cutoff_issues.out.csv", help="결과 CSV")
    p.add_argument("--close-date", required=True, help="마감일 (예: 2026-10-05). 이 날 다음부터 입력된 건은 지난달 전기 불가")
    p.add_argument("--backdate-days", type=int, default=30, help="입력일보다 전기일이 며칠 넘게 과거면 소급 의심 (기본 30)")
    p.add_argument("--no-weekend", action="store_true", help="주말 전기 점검을 끕니다")
    p.add_argument("--col-id", default="전표번호")
    p.add_argument("--col-txn", default="거래일")
    p.add_argument("--col-post", default="전기일")
    p.add_argument("--col-entry", default="입력일")
    p.add_argument("--col-amount", default="차변")
    p.add_argument("--encoding", default="utf-8-sig")
    a = p.parse_args()

    close = to_date(a.close_date)
    if not close:
        raise SystemExit("[오류] --close-date 형식이 틀렸습니다. 예: 2026-10-05")
    # 마감일이 속한 달의 '바로 전 달 말일'까지가 마감된 기간이라고 봅니다.
    closed_until = date(close.year, close.month, 1)

    vouchers = OrderedDict()
    with open(a.input, encoding=a.encoding, newline="") as f:
        reader = csv.DictReader(f)
        need = [a.col_id, a.col_txn, a.col_post, a.col_entry, a.col_amount]
        miss = [c for c in need if c not in (reader.fieldnames or [])]
        if miss:
            raise SystemExit(f"[오류] 열이 없습니다: {miss} / 있는 열: {reader.fieldnames}")
        for row in reader:
            vid = row[a.col_id].strip()
            v = vouchers.setdefault(vid, {"row": row, "amount": 0.0})
            v["amount"] += to_num(row[a.col_amount])

    issues = []
    count = defaultdict(int)
    total = defaultdict(float)
    bad_date = 0
    for vid, v in vouchers.items():
        r = v["row"]
        txn, post, entry = to_date(r[a.col_txn]), to_date(r[a.col_post]), to_date(r[a.col_entry])
        if not (txn and post and entry):
            bad_date += 1
            issues.append([vid, r[a.col_txn], r[a.col_post], r[a.col_entry], f"{v['amount']:.0f}", "DATE_ERROR", "날짜를 읽을 수 없음"])
            continue
        reasons = []
        if (txn.year, txn.month) != (post.year, post.month):
            reasons.append(("MONTH_DIFF", f"거래 {txn:%Y-%m} / 전기 {post:%Y-%m}"))
        if entry > close and post < closed_until:
            reasons.append(("AFTER_CLOSE", f"마감({close}) 뒤 입력인데 마감된 기간에 전기"))
        if not a.no_weekend and post.weekday() >= 5:
            reasons.append(("WEEKEND", "전기일이 주말"))
        if (entry - post).days > a.backdate_days:
            reasons.append(("BACKDATED", f"입력일보다 {(entry - post).days}일 과거로 전기"))
        for code, why in reasons:
            count[code] += 1
            total[code] += v["amount"]
            issues.append([vid, r[a.col_txn], r[a.col_post], r[a.col_entry], f"{v['amount']:.0f}", code, why])

    with open(a.output, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["전표번호", "거래일", "전기일", "입력일", "차변합계", "사유코드", "설명"])
        w.writerows(issues)

    print(f"전표 {len(vouchers)}건 점검, 의심 {len(issues)}줄 → {a.output}")
    for code in ("MONTH_DIFF", "AFTER_CLOSE", "WEEKEND", "BACKDATED"):
        print(f"  {code:12s} {count[code]:4d}건  금액 {total[code]:,.0f}")
    if bad_date:
        print(f"  DATE_ERROR   {bad_date:4d}건 (날짜 형식 확인 필요)")


if __name__ == "__main__":
    main()
