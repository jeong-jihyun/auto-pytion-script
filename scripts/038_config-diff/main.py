"""설정 파일 비교(개발/운영 환경 차이 점검) 스크립트.

두 설정 파일(.json 또는 .env/.ini 식 KEY=VALUE)을 비교해
 - 한쪽에만 있는 항목
 - 값이 다른 항목
을 알려 줍니다. JSON 안쪽 구조는 'db.host' 처럼 점으로 펼쳐서 비교합니다.
password/secret/token/key 가 이름에 든 항목은 값을 화면에 보여 주지 않고 '(가림)' 으로 표시합니다.
"""
import argparse
import json
import sys
from pathlib import Path

SECRET_WORDS = ("password", "passwd", "secret", "token", "key", "pwd", "비밀")


def flatten(obj, prefix=""):
    """중첩된 JSON 을 {'a.b': 값} 모양으로 펼칩니다."""
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(flatten(v, f"{prefix}{k}."))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.update(flatten(v, f"{prefix}{i}."))
    else:
        out[prefix[:-1]] = obj
    return out


def load(path):
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() == ".json":
        return flatten(json.loads(text))
    res = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith(("#", ";", "[")) or "=" not in line:
            continue
        k, v = line.split("=", 1)
        res[k.strip()] = v.strip().strip('"').strip("'")
    return res


def show(key, value):
    return "(가림)" if any(w in key.lower() for w in SECRET_WORDS) else repr(value)


def main():
    p = argparse.ArgumentParser(description="설정 파일 두 개 비교")
    p.add_argument("a", type=Path, help="기준 파일(예: 개발)")
    p.add_argument("b", type=Path, help="비교 파일(예: 운영)")
    p.add_argument("--ignore", default="", help="무시할 항목 이름(쉼표로 구분)")
    args = p.parse_args()

    ignore = {s.strip() for s in args.ignore.split(",") if s.strip()}
    A, B = load(args.a), load(args.b)
    only_a = sorted(k for k in A if k not in B and k not in ignore)
    only_b = sorted(k for k in B if k not in A and k not in ignore)
    diff = sorted(k for k in A if k in B and A[k] != B[k] and k not in ignore)

    print(f"기준 {args.a.name} ({len(A)}개) vs 비교 {args.b.name} ({len(B)}개)")
    for k in only_a:
        print(f"  [기준에만 있음] {k} = {show(k, A[k])}")
    for k in only_b:
        print(f"  [비교에만 있음] {k} = {show(k, B[k])}")
    for k in diff:
        print(f"  [값 다름] {k}: {show(k, A[k])} -> {show(k, B[k])}")
    if not (only_a or only_b or diff):
        print("차이가 없습니다.")
    sys.exit(1 if (only_a or only_b or diff) else 0)


if __name__ == "__main__":
    main()
