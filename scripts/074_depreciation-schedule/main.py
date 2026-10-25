"""고정자산 감가상각 일정표(정액법·정률법)를 만드는 스크립트.

생각의 흐름:
  - 정액법: 해마다 (취득가 - 잔존가) / 내용연수 만큼 똑같이 줄입니다.
  - 정률법: 해마다 '남은 장부가 × 상각률'만큼 줄입니다. 상각률은 1 - (잔존가/취득가)^(1/내용연수).
    잔존가가 0이면 계산이 안 되므로, 이때는 취득가의 5%를 계산용 잔존가로 쓰고 마지막 해에 남은 금액을 모두 상각합니다.
  - 첫해는 취득 월부터 12월까지 월할(月割)로 계산합니다(--monthly 를 끄면 1년치 전체).
  - 원 단위 미만은 버리고, 마지막 해에 끝수를 맞춰 장부가가 정확히 잔존가가 되게 합니다.
여러 자산은 CSV로 넣어 자산별·연도별 표를 한 번에 만듭니다.
"""
import argparse
import csv
import sys
from decimal import Decimal, ROUND_FLOOR
from pathlib import Path

ONE = Decimal(1)


def floor_won(x):
    return x.quantize(ONE, rounding=ROUND_FLOOR)


def schedule(cost, salvage, years, method, start_year, start_month, monthly=True):
    """[(연도, 상각액, 기말장부가)] 목록을 돌려줍니다."""
    cost, salvage = Decimal(cost), Decimal(salvage)
    if years <= 0 or cost <= 0 or salvage < 0 or salvage >= cost:
        raise ValueError("취득가>잔존가>=0, 내용연수>0 이어야 합니다")
    months_total = years * 12
    first_months = (12 - start_month + 1) if monthly else 12
    rows, book, used = [], cost, 0
    if method == "정률":
        base_salvage = salvage if salvage > 0 else cost * Decimal("0.05")
        rate = ONE - (base_salvage / cost) ** (ONE / Decimal(years))
    year = start_year
    while used < months_total:
        m = min(first_months if used == 0 else 12, months_total - used)
        last = used + m >= months_total
        if last:
            dep = book - salvage
        elif method == "정액":
            dep = floor_won((cost - salvage) * m / months_total)
        else:
            dep = floor_won(book * rate * m / 12)
            dep = min(dep, book - salvage)
        book -= dep
        used += m
        rows.append((year, m, dep, book))
        year += 1
    return rows


def main():
    p = argparse.ArgumentParser(description="감가상각 일정표")
    p.add_argument("input", type=Path, help="자산 CSV(자산명,취득가,잔존가,내용연수,방법,취득일)")
    p.add_argument("--no-monthly", action="store_true", help="첫해도 12개월로 계산")
    p.add_argument("-o", "--output", type=Path, default=Path("output/depreciation.csv"))
    a = p.parse_args()

    out, errors = [], 0
    with a.input.open(newline="", encoding="utf-8-sig") as fp:
        for r in csv.DictReader(fp):
            name = r["자산명"]
            try:
                y, mo = (int(x) for x in r["취득일"].split("-")[:2])
                rows = schedule(r["취득가"].replace(",", ""), (r.get("잔존가") or "0").replace(",", ""),
                                int(r["내용연수"]), r["방법"].strip(), y, mo, not a.no_monthly)
            except (ValueError, KeyError) as e:
                print(f"[건너뜀] {name}: {e}")
                errors += 1
                continue
            if r["방법"].strip() not in ("정액", "정률"):
                print(f"[건너뜀] {name}: 방법은 정액/정률 중 하나")
                errors += 1
                continue
            acc = Decimal(0)
            for year, months, dep, book in rows:
                acc += dep
                out.append({"자산명": name, "방법": r["방법"].strip(), "연도": year, "상각개월": months,
                            "상각액": str(dep), "누계액": str(acc), "기말장부가": str(book)})
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.DictWriter(fp, fieldnames=["자산명", "방법", "연도", "상각개월", "상각액", "누계액", "기말장부가"])
        w.writeheader()
        w.writerows(out)
    print(f"{len(out)}줄 작성(건너뛴 자산 {errors}개) → {a.output}")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
