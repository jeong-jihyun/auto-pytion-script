"""감사·검수용 표본(샘플)을 CSV에서 뽑는 스크립트.

- random    : 무작위로 N건 (같은 --seed 면 항상 같은 결과 -> 나중에 재현 가능)
- systematic: 시작 위치를 정한 뒤 일정 간격(전체/N)으로 뽑기
- 금액 열을 주면 --top-amount 로 '큰 금액 상위 K건'을 반드시 포함(전수 검토 대상)할 수 있습니다.
어떤 방법·씨앗값·모집단 크기로 뽑았는지 요약 파일에 남겨, 검수 기록으로 쓸 수 있습니다.
"""
import argparse
import csv
import random
import sys
from pathlib import Path


def to_num(text):
    try:
        return float(str(text).replace(",", "").strip())
    except ValueError:
        return float("-inf")


def main():
    p = argparse.ArgumentParser(description="감사·검수 표본 추출")
    p.add_argument("input", type=Path)
    p.add_argument("-n", "--size", type=int, required=True, help="뽑을 건수(상위 금액 포함분 제외)")
    p.add_argument("--method", choices=["random", "systematic"], default="random")
    p.add_argument("--seed", type=int, default=2026, help="무작위 씨앗값(같으면 같은 결과)")
    p.add_argument("--amount-col", help="금액 열 이름(상위 금액 포함 기능에 사용)")
    p.add_argument("--top-amount", type=int, default=0, help="금액 큰 순 K건은 무조건 포함")
    p.add_argument("-o", "--output-dir", type=Path, default=Path("output"))
    a = p.parse_args()

    with a.input.open(newline="", encoding="utf-8-sig") as fp:
        r = csv.DictReader(fp)
        fields = list(r.fieldnames or [])
        rows = list(r)
    if a.top_amount and a.amount_col not in fields:
        print(f"[오류] --top-amount 는 있는 열을 --amount-col 로 알려 줘야 합니다. (열: {fields})")
        sys.exit(1)

    picked_idx = set()
    if a.top_amount:
        order = sorted(range(len(rows)), key=lambda i: -to_num(rows[i][a.amount_col]))
        picked_idx.update(order[:a.top_amount])
    rest = [i for i in range(len(rows)) if i not in picked_idx]
    size = min(a.size, len(rest))
    rng = random.Random(a.seed)
    if a.method == "random":
        chosen = rng.sample(rest, size)
    else:
        step = len(rest) / size if size else 1
        start = rng.random() * step
        chosen = [rest[int(start + k * step)] for k in range(size)]
    picked_idx.update(chosen)

    a.output_dir.mkdir(parents=True, exist_ok=True)
    out = sorted(picked_idx)
    with (a.output_dir / "sample.csv").open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["원본줄번호"] + fields + ["구분"])
        for i in out:
            tag = "상위금액" if (a.top_amount and i in set(order[:a.top_amount])) else "표본"
            w.writerow([i + 2] + [rows[i][f] for f in fields] + [tag])
    summary = (f"방법={a.method}, seed={a.seed}, 모집단={len(rows)}건, "
               f"상위금액 포함={a.top_amount}건, 표본={len(chosen)}건, 총 검토 대상={len(out)}건")
    (a.output_dir / "sample_summary.txt").write_text(summary + "\n", encoding="utf-8")
    print("[완료]", summary, f"-> {a.output_dir}/sample.csv")


if __name__ == "__main__":
    main()
