"""CSV의 고객번호·이름 같은 식별 열을 '같은 값은 항상 같은 가명'으로 바꾸는(가명처리) 스크립트.

생각의 흐름:
  1) 별표(***)로 가리는 마스킹은 안전하지만, 가린 뒤에는 '같은 고객의 거래끼리 묶기'나
     '두 파일을 고객 기준으로 잇기'를 할 수 없습니다. 분석·테스트 데이터에는 그게 필요합니다.
  2) 그래서 비밀 키로 HMAC-SHA256 값을 만들어 가명으로 씁니다.
       - 같은 원본 + 같은 키 → 항상 같은 가명 (파일이 달라도 이어 붙일 수 있음)
       - 키를 모르면 가명에서 원본을 거꾸로 알아내기 어렵습니다. (단순 해시는 전화번호처럼
         경우의 수가 적은 값은 모두 대입해 보면 풀리므로, 반드시 비밀 키를 섞습니다.)
  3) 키는 코드나 명령 인자에 넣지 않고 환경변수(기본 PSEUDO_KEY)에서만 읽습니다. 없으면 멈춥니다.
  4) 열마다 접두어를 붙여(CUST_1a2b…) 어떤 열의 가명인지 알아보기 쉽게 했습니다.
  5) 원본↔가명 대응표는 재식별이 가능해지는 위험한 파일이라 기본으로 만들지 않고,
     --mapping 을 줄 때만 만들고 경고를 보여 줍니다.
  6) 빈칸은 빈칸 그대로 둡니다(빈칸까지 가명으로 바꾸면 모두 같은 가명이 되어 오해를 부릅니다).
"""
import argparse
import csv
import hashlib
import hmac
import os
import sys


def token(key, column, value, length):
    # 열 이름도 섞어서, 같은 값이라도 열이 다르면 다른 가명이 되게 합니다(원하면 --same-across-columns)
    msg = f"{column}\x1f{value}".encode("utf-8")
    return hmac.new(key, msg, hashlib.sha256).hexdigest()[:length]


def main():
    p = argparse.ArgumentParser(description="CSV 식별 열 가명처리(HMAC)")
    p.add_argument("input")
    p.add_argument("-c", "--columns", required=True,
                   help="가명으로 바꿀 열과 접두어. 예: 고객번호:CUST,이름:NAME,전화:TEL")
    p.add_argument("-o", "--output", default="pseudonymized.out.csv")
    p.add_argument("--key-env", default="PSEUDO_KEY", help="비밀 키를 읽을 환경변수 이름(기본 PSEUDO_KEY)")
    p.add_argument("--length", type=int, default=12, help="가명 길이(16진수 글자 수, 기본 12)")
    p.add_argument("--same-across-columns", action="store_true",
                   help="열이 달라도 같은 값이면 같은 가명(예: 보낸고객·받는고객 열)")
    p.add_argument("--mapping", help="원본↔가명 대응표 CSV 경로(재식별 가능! 별도 보관)")
    p.add_argument("--encoding", default="utf-8-sig")
    a = p.parse_args()

    key = os.environ.get(a.key_env, "")
    if len(key) < 16:
        sys.exit(f"환경변수 {a.key_env} 에 16자 이상 비밀 키를 넣어 주세요. (.env.example 참고)")
    keyb = key.encode("utf-8")

    spec = []
    for part in a.columns.split(","):
        col, _, prefix = part.partition(":")
        spec.append((col.strip(), (prefix.strip() or col.strip()).upper()))

    with open(a.input, newline="", encoding=a.encoding) as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        rows = list(reader)
    missing = [c for c, _ in spec if c not in fields]
    if missing:
        sys.exit(f"CSV에 없는 열: {', '.join(missing)} (있는 열: {', '.join(fields)})")

    mapping = {}
    for r in rows:
        for col, prefix in spec:
            v = (r.get(col) or "").strip()
            if not v:
                continue
            scope = "*" if a.same_across_columns else col
            t = f"{prefix}_{token(keyb, scope, v, a.length)}"
            mapping[(col, v)] = t
            r[col] = t

    with open(a.output, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    # 가명 충돌(다른 원본이 같은 가명) 확인: 길이를 너무 짧게 잡았을 때 생길 수 있음
    seen, collisions = {}, 0
    for (col, v), t in mapping.items():
        if t in seen and seen[t] != v:
            collisions += 1
        seen[t] = v

    print(f"{len(rows)}행 가명처리 → {a.output}")
    for col, prefix in spec:
        n = len({v for (c, v) in mapping if c == col})
        print(f"  {col}: 서로 다른 값 {n}개 → {prefix}_xxxx")
    if collisions:
        print(f"  ⚠ 가명 충돌 {collisions}건: --length 를 늘리세요")
    if a.mapping:
        with open(a.mapping, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["열", "원본", "가명"])
            for (col, v), t in sorted(mapping.items()):
                w.writerow([col, v, t])
        print(f"  ⚠ 대응표 {a.mapping} 는 원본을 되찾을 수 있는 파일입니다. 가명 파일과 따로, 접근을 제한해 보관하세요.")


if __name__ == "__main__":
    main()
