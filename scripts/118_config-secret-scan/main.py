"""설정 파일에 비밀번호·토큰이 '평문'으로 적혀 있는지 찾아 주는 점검 스크립트(내 파일 점검용).

생각의 흐름:
  1) 운영 설정 파일(.properties, .yml, .env, .ini …)에 DB 비밀번호가 그대로 적혀 저장소나
     공유 폴더에 올라가는 사고가 자주 납니다. 배포 전에 미리 찾아 고치는 것이 목적입니다.
  2) 찾는 방법은 두 가지입니다.
     - 이름 규칙: password, passwd, pwd, secret, token, api_key 같은 키에 값이 들어 있는 줄
     - 모양 규칙: 개인키 시작 줄, URL 안의 '아이디:비밀번호@' 형태
  3) ${DB_PASSWORD}, <비밀번호>, 빈 값처럼 '자리표시자'는 정상(환경변수 사용)으로 보고 넘어갑니다.
  4) 보고서에도 비밀이 새지 않도록 값은 앞 2글자만 남기고 가립니다.
  5) 파일을 고치거나 지우지 않습니다. 읽기만 합니다.
"""
import argparse
import csv
import re
from pathlib import Path

EXTS = {".env", ".properties", ".yml", ".yaml", ".ini", ".conf", ".cfg", ".json", ".xml", ".toml", ".py", ".sh"}
KEY_RE = re.compile(
    r"""(?P<key>[\w.\-]*(?:password|passwd|pwd|secret|token|api[_\-]?key|access[_\-]?key)[\w.\-]*)"""
    r"""\s*["']?\s*[:=]\s*["']?(?P<val>[^"'\s,#;<>]*)""", re.I)
URL_RE = re.compile(r"[a-z][a-z0-9+.\-]*://[^/\s:@]+:(?P<val>[^@\s/]+)@", re.I)
PEM_RE = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
PLACEHOLDER = re.compile(r"^(\$\{.*\}|\$\w+|%\w+%|\{\{.*\}\}|<.*>|\*+|x+|changeme|null|none|true|false|)$", re.I)


def mask(v):
    return (v[:2] + "*" * max(len(v) - 2, 3)) if v else ""


def scan_line(line):
    """한 줄에서 의심 항목을 (종류, 키, 가린 값) 목록으로 돌려줍니다."""
    found = []
    if PEM_RE.search(line):
        found.append(("개인키", "PRIVATE KEY", "-----"))
    for m in URL_RE.finditer(line):
        if not PLACEHOLDER.match(m.group("val")):
            found.append(("URL안 비밀번호", "url", mask(m.group("val"))))
    for m in KEY_RE.finditer(line):
        v = m.group("val")
        if not PLACEHOLDER.match(v) and "://" not in line:
            found.append(("평문 비밀값", m.group("key"), mask(v)))
    return found


def main():
    p = argparse.ArgumentParser(description="설정 파일 평문 비밀번호 점검")
    p.add_argument("folder", type=Path, help="점검할 폴더")
    p.add_argument("--all-files", action="store_true", help="확장자와 상관없이 모든 텍스트 파일 점검")
    p.add_argument("-o", "--output", type=Path, default=Path("output/secret_scan.csv"))
    a = p.parse_args()

    rows, files = [], 0
    for f in sorted(a.folder.rglob("*")):
        if not f.is_file() or ".git" in f.parts:
            continue
        if not a.all_files and f.suffix.lower() not in EXTS and not f.name.startswith(".env"):
            continue
        files += 1
        try:
            text = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue  # 바이너리·읽을 수 없는 파일은 건너뜀
        for no, line in enumerate(text.splitlines(), 1):
            for kind, key, val in scan_line(line):
                rows.append([str(f.relative_to(a.folder)), no, kind, key, val])

    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["파일", "줄", "종류", "키", "값(가림)"])
        w.writerows(rows)
    print(f"파일 {files}개 점검, 의심 {len(rows)}건 → {a.output}")
    for r in rows:
        print(f"  {r[0]}:{r[1]} [{r[2]}] {r[3]} = {r[4]}")
    if rows:
        print("→ 값은 환경변수나 비밀 관리 도구로 옮기고, 이미 공유됐다면 비밀번호를 바꾸세요.")


if __name__ == "__main__":
    main()
