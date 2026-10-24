"""'거의 같은' 이름(거래처·고객명)을 찾아 중복 후보로 알려 주는 스크립트.

'(주)가나다', '가나다 주식회사', '가나다' 처럼 표기만 다른 이름을 같은 것으로 보고,
글자 하나가 다른 오타('가나다상사' / '가나다상서')도 비슷한 정도(0~1)로 찾습니다.
합치기는 하지 않고 후보 목록만 만듭니다. 최종 판단은 사람이 합니다.
"""
import argparse
import csv
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

NOISE = ["주식회사", "유한회사", "(주)", "㈜", "(유)", "co.,ltd", "co.ltd", "inc."]


def normalize(name):
    """비교하기 쉽게 법인 표시·공백·특수문자를 없애고 소문자로 만듭니다."""
    s = name.lower()
    for n in NOISE:
        s = s.replace(n, "")
    return re.sub(r"[\s\-_.,()·]", "", s)


def main():
    p = argparse.ArgumentParser(description="비슷한 이름 중복 후보 찾기")
    p.add_argument("input", type=Path)
    p.add_argument("--column", required=True, help="이름이 있는 열")
    p.add_argument("--threshold", type=float, default=0.8, help="이 값 이상 비슷하면 후보(0~1)")
    p.add_argument("-o", "--output", type=Path, default=Path("output/fuzzy_pairs.csv"))
    a = p.parse_args()

    with a.input.open(newline="", encoding="utf-8-sig") as fp:
        r = csv.DictReader(fp)
        if a.column not in (r.fieldnames or []):
            print(f"[오류] 없는 열: {a.column} (있는 열: {r.fieldnames})")
            sys.exit(1)
        names = [(i + 2, row[a.column].strip()) for i, row in enumerate(r) if row[a.column].strip()]

    keyed = [(ln, nm, normalize(nm)) for ln, nm in names]
    pairs = []
    for i in range(len(keyed)):
        for j in range(i + 1, len(keyed)):
            (l1, n1, k1), (l2, n2, k2) = keyed[i], keyed[j]
            if not k1 or not k2:
                continue
            if abs(len(k1) - len(k2)) > max(len(k1), len(k2)) * (1 - a.threshold) + 1:
                continue                       # 길이 차이가 너무 크면 비교 생략(속도)
            score = 1.0 if k1 == k2 else SequenceMatcher(None, k1, k2).ratio()
            if score >= a.threshold:
                pairs.append((round(score, 3), l1, n1, l2, n2, "표기만 다름" if k1 == k2 else "비슷함"))
    pairs.sort(key=lambda x: -x[0])

    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["유사도", "줄번호1", "이름1", "줄번호2", "이름2", "판정"])
        w.writerows(pairs)
    print(f"[완료] 이름 {len(names)}개 비교, 중복 후보 {len(pairs)}쌍 -> {a.output}")
    for s, l1, n1, l2, n2, kind in pairs:
        print(f"  - {s}: [{l1}] {n1}  <->  [{l2}] {n2} ({kind})")


if __name__ == "__main__":
    main()
