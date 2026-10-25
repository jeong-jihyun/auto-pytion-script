"""사업자등록번호(10자리)의 형식과 검증번호(마지막 자리)를 확인하는 스크립트.

거래처 마스터에 번호를 잘못 입력하면 세금계산서가 반려됩니다.
생각의 흐름:
  1) 하이픈·공백을 빼고 숫자 10자리인지 봅니다.
  2) 앞 9자리에 가중치 1,3,7,1,3,7,1,3,5를 곱해 더하고,
     9번째 자리×5의 십의 자리를 한 번 더 더합니다.
  3) (10 - 합계 % 10) % 10 이 마지막 자리와 같으면 '형식상 올바름'.
주의: 이 검사는 '번호 모양이 맞는지'만 봅니다. 실제 등록·휴폐업 여부는 국세청 조회가 필요합니다.
"""
import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

WEIGHTS = [1, 3, 7, 1, 3, 7, 1, 3, 5]


def clean(text):
    return "".join(ch for ch in (text or "") if ch.isdigit())


def check(text):
    """(결과, 정리된 번호) 를 돌려줍니다. 결과는 '정상' 또는 문제 설명."""
    raw = (text or "").strip()
    if not raw:
        return "빈 값", ""
    if any(not (c.isdigit() or c in "- ") for c in raw):
        return "숫자·하이픈 외 글자 있음", ""
    d = clean(raw)
    if len(d) != 10:
        return f"자릿수 오류({len(d)}자리)", d
    nums = [int(c) for c in d]
    total = sum(n * w for n, w in zip(nums[:9], WEIGHTS))
    total += (nums[8] * 5) // 10
    expect = (10 - total % 10) % 10
    if expect != nums[9]:
        return f"검증번호 불일치(기대 {expect})", d
    return "정상", d


def pretty(d):
    return f"{d[:3]}-{d[3:5]}-{d[5:]}" if len(d) == 10 else d


def main():
    p = argparse.ArgumentParser(description="사업자등록번호 형식·검증번호 점검")
    p.add_argument("input", type=Path, help="CSV 파일")
    p.add_argument("--col", default="사업자번호")
    p.add_argument("-o", "--output", type=Path, default=Path("output/bizno_check.csv"))
    a = p.parse_args()

    with a.input.open(newline="", encoding="utf-8-sig") as fp:
        r = csv.DictReader(fp)
        fields = list(r.fieldnames or [])
        if a.col not in fields:
            print(f"[오류] 없는 열: {a.col} (있는 열: {fields})")
            sys.exit(1)
        rows = list(r)

    seen = Counter(clean(row[a.col]) for row in rows if clean(row[a.col]))
    stats = Counter()
    for row in rows:
        result, d = check(row[a.col])
        if result == "정상" and seen[d] > 1:
            result = "정상(중복 등록)"
        row["점검결과"] = result
        row["표준형식"] = pretty(d) if result.startswith("정상") else ""
        stats["정상" if result.startswith("정상") else "문제"] += 1

    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.DictWriter(fp, fieldnames=fields + ["점검결과", "표준형식"])
        w.writeheader()
        w.writerows(rows)
    print(f"전체 {len(rows)}건: 정상 {stats['정상']}건, 문제 {stats['문제']}건 → {a.output}")


if __name__ == "__main__":
    main()
