"""체결내역 종목별 요약 스크립트.

하루치 체결내역 CSV를 읽어서 종목별로
  매수/매도 수량, 매수/매도 평균단가(수량 가중), 매수/매도 금액, 순수량(매수-매도), 수수료 합계
를 계산합니다. 금액은 Decimal 로 계산해 소수점 오차가 없습니다.
- 수량이 0 이하이거나 구분이 '매수/매도'가 아닌 줄은 합계에서 빼고 '오류 목록'으로 따로 보여 줍니다.
입력 열: 종목코드, 종목명, 구분, 수량, 단가, 수수료
"""
import argparse
import csv
import sys
from collections import OrderedDict
from decimal import Decimal, InvalidOperation
from pathlib import Path


def 숫자(글):
    return Decimal(str(글).replace(",", "").strip())


def main():
    p = argparse.ArgumentParser(description="체결내역 종목별 요약")
    p.add_argument("input", help="체결내역 CSV")
    p.add_argument("-o", "--output", default="output/trade_summary.csv")
    p.add_argument("--encoding", default="utf-8-sig")
    a = p.parse_args()

    종목 = OrderedDict()
    오류 = []
    with open(a.input, newline="", encoding=a.encoding) as fp:
        for 번호, 행 in enumerate(csv.DictReader(fp), start=2):  # 머리글이 1줄이라 데이터는 2줄부터
            try:
                구분 = 행["구분"].strip()
                수량, 단가 = 숫자(행["수량"]), 숫자(행["단가"])
                수수료 = 숫자(행.get("수수료") or "0")
                if 구분 not in ("매수", "매도"):
                    raise ValueError(f"구분이 '{구분}' 입니다(매수/매도만 가능)")
                if 수량 <= 0 or 단가 < 0:
                    raise ValueError("수량은 1 이상, 단가는 0 이상이어야 합니다")
            except (InvalidOperation, ValueError, KeyError) as e:
                오류.append((번호, str(e)))
                continue
            d = 종목.setdefault(행["종목코드"].strip(), {
                "종목명": 행["종목명"].strip(), "매수수량": Decimal(0), "매수금액": Decimal(0),
                "매도수량": Decimal(0), "매도금액": Decimal(0), "수수료": Decimal(0)})
            접두 = "매수" if 구분 == "매수" else "매도"
            d[접두 + "수량"] += 수량
            d[접두 + "금액"] += 수량 * 단가
            d["수수료"] += 수수료

    def 평균(금액, 수량):
        return (금액 / 수량).quantize(Decimal("0.01")) if 수량 else Decimal(0)

    out = Path(a.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    총수수료 = Decimal(0)
    with out.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["종목코드", "종목명", "매수수량", "매수평균단가", "매수금액",
                    "매도수량", "매도평균단가", "매도금액", "순수량", "수수료합계"])
        for 코드, d in 종목.items():
            w.writerow([코드, d["종목명"], d["매수수량"], 평균(d["매수금액"], d["매수수량"]), d["매수금액"],
                        d["매도수량"], 평균(d["매도금액"], d["매도수량"]), d["매도금액"],
                        d["매수수량"] - d["매도수량"], d["수수료"]])
            총수수료 += d["수수료"]
    print(f"완료: 종목 {len(종목)}개, 수수료 합계 {총수수료:,} -> {out}")
    if 오류:
        print(f"[주의] 합계에서 뺀 줄 {len(오류)}개:")
        for 번호, 이유 in 오류:
            print(f"  {번호}번째 줄: {이유}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
