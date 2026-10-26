"""입금 1건이 청구 여러 건을 합쳐서 낸 것인지 '금액 조합'으로 찾아 주는 스크립트.

생각의 흐름:
  1) 거래처가 청구서 3장을 한 번에 묶어 입금하면, 키(청구번호)가 없어 대사가 안 됩니다.
  2) 그래서 같은 거래처의 미결 청구 중에서 '합계가 입금액과 같은 조합'을 찾습니다.
     먼저 1건짜리, 그다음 2건, 3건… 순서로 찾아 가장 적은 건수의 조합을 고릅니다.
  3) 조합 수는 빠르게 늘어나므로 최대 건수(--max-items)와 거래처별 후보 수(--max-candidates)를 제한합니다.
  4) 한 번 쓰인 청구는 다른 입금에 다시 쓰지 않습니다. 큰 입금부터 처리해 엉뚱한 작은 조합이 먼저 먹지 않게 합니다.
  5) 매칭 결과와 남은 입금·청구를 CSV로 저장합니다. 결과는 '제안'이니 사람이 확인해야 합니다.
"""
import argparse
import csv
from decimal import Decimal
from itertools import combinations
from pathlib import Path


def read(path, id_col):
    with path.open(newline="", encoding="utf-8-sig") as fp:
        return [{"id": r[id_col].strip(), "who": r["거래처"].strip(),
                 "amt": Decimal(r["금액"].replace(",", "").strip())} for r in csv.DictReader(fp)]


def find_combo(target, cands, max_items, tol):
    """cands(청구 목록) 중 합계가 target±tol 인 가장 적은 건수 조합을 찾습니다."""
    for k in range(1, max_items + 1):
        for combo in combinations(cands, k):
            if abs(sum(c["amt"] for c in combo) - target) <= tol:
                return combo
    return None


def main():
    p = argparse.ArgumentParser(description="입금-청구 금액 조합 매칭")
    p.add_argument("deposits", type=Path, help="입금 CSV(입금ID,거래처,금액)")
    p.add_argument("invoices", type=Path, help="청구 CSV(청구ID,거래처,금액)")
    p.add_argument("--max-items", type=int, default=4, help="한 입금에 묶일 최대 청구 수(기본 4)")
    p.add_argument("--max-candidates", type=int, default=20, help="거래처별로 살펴볼 청구 수 상한(기본 20)")
    p.add_argument("--tolerance", type=Decimal, default=Decimal("0"), help="허용 차액(예: 송금수수료 500)")
    p.add_argument("-o", "--outdir", type=Path, default=Path("output"))
    a = p.parse_args()

    deps = sorted(read(a.deposits, "입금ID"), key=lambda d: -d["amt"])
    invs = read(a.invoices, "청구ID")
    used, matches, left_deps = set(), [], []
    for d in deps:
        cands = [i for i in invs if i["who"] == d["who"] and i["id"] not in used][: a.max_candidates]
        combo = find_combo(d["amt"], cands, a.max_items, a.tolerance)
        if combo:
            used.update(c["id"] for c in combo)
            total = sum(c["amt"] for c in combo)
            matches.append([d["id"], d["who"], d["amt"], ";".join(c["id"] for c in combo), total, d["amt"] - total])
        else:
            left_deps.append([d["id"], d["who"], d["amt"]])
    left_invs = [[i["id"], i["who"], i["amt"]] for i in invs if i["id"] not in used]

    a.outdir.mkdir(parents=True, exist_ok=True)
    def save(name, head, rows):
        with (a.outdir / name).open("w", newline="", encoding="utf-8-sig") as fp:
            w = csv.writer(fp); w.writerow(head); w.writerows(rows)
    save("matched.csv", ["입금ID", "거래처", "입금액", "매칭청구ID", "청구합계", "차액"], matches)
    save("unmatched_deposits.csv", ["입금ID", "거래처", "금액"], left_deps)
    save("unmatched_invoices.csv", ["청구ID", "거래처", "금액"], left_invs)

    print(f"입금 {len(deps)}건 중 매칭 {len(matches)}건, 미매칭 입금 {len(left_deps)}건, 남은 청구 {len(left_invs)}건")
    for m in matches:
        print(f"  {m[0]}({m[1]}) {m[2]:,} ← {m[3]} (차액 {m[5]:,})")
    print(f"결과 폴더: {a.outdir}")


if __name__ == "__main__":
    main()
