"""환경설정(.env) 점검 스크립트.

'.env.example'(필요한 키 목록)과 실제 '.env' 를 비교해서
빠진 키, 값이 빈 키, 예시에 없는 키를 알려 줍니다.
비밀번호·API 키 보호를 위해 값은 절대 화면에 출력하지 않고 키 이름만 보여 줍니다.
점검에서 문제가 있으면 종료 코드 1 을 돌려줘서 배치에서도 쓸 수 있습니다.
"""
import argparse
import sys
from pathlib import Path


def read_env(path):
    """KEY=VALUE 줄을 읽어 {키: 값} 으로 돌려줍니다. # 주석과 빈 줄은 건너뜁니다."""
    data = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export "):]
        key, _, val = line.partition("=")
        data[key.strip()] = val.strip().strip('"').strip("'")
    return data


def main():
    p = argparse.ArgumentParser(description=".env 와 .env.example 비교 점검")
    p.add_argument("--example", type=Path, required=True, help="필요한 키가 적힌 예시 파일")
    p.add_argument("--env", type=Path, required=True, help="점검할 실제 설정 파일")
    a = p.parse_args()
    for f in (a.example, a.env):
        if not f.is_file():
            raise SystemExit(f"오류: 파일이 없습니다: {f}")

    need, have = read_env(a.example), read_env(a.env)
    missing = [k for k in need if k not in have]
    empty = [k for k in need if k in have and have[k] == ""]
    extra = [k for k in have if k not in need]
    for title, keys in (("빠진 키", missing), ("값이 빈 키", empty), ("예시에 없는 키", extra)):
        print(f"{title} {len(keys)}개" + (": " + ", ".join(keys) if keys else ""))
    ok = not missing and not empty
    print("결과:", "통과" if ok else "문제 있음 (빠진 키·빈 키를 채워 주세요)")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
