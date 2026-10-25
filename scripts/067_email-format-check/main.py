"""CSV의 이메일 주소가 올바른 모양인지 점검하는 스크립트(발송은 하지 않음).

모양 점검(@ 하나, 도메인에 점, 공백·한글 등 금지), 흔한 오타 도메인(gmial.com 등) 추정,
같은 주소 중복, 도메인별 개수를 알려 줍니다. 실제로 메일이 가는지는 확인하지 않습니다.
"""
import argparse
import csv
import re
import sys
from collections import Counter
from pathlib import Path

PATTERN = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(\.[A-Za-z0-9\-]+)+$")
# 자주 틀리는 도메인 → 맞는 도메인 추정
TYPOS = {"gmial.com": "gmail.com", "gamil.com": "gmail.com", "gmail.co": "gmail.com",
         "naver.co": "naver.com", "naber.com": "naver.com", "nate.co": "nate.com",
         "hanmial.net": "hanmail.net", "hotmial.com": "hotmail.com", "daum.com": "daum.net"}


def main():
    p = argparse.ArgumentParser(description="이메일 주소 형식 점검")
    p.add_argument("input", type=Path)
    p.add_argument("--column", default="이메일")
    p.add_argument("-o", "--output", type=Path, default=Path("output/email_check.csv"))
    a = p.parse_args()

    with a.input.open(newline="", encoding="utf-8-sig") as fp:
        r = csv.DictReader(fp)
        fields = r.fieldnames or []
        if a.column not in fields:
            print(f"[오류] 없는 열: {a.column} (있는 열: {fields})")
            sys.exit(1)
        rows = list(r)

    seen = Counter(x[a.column].strip().lower() for x in rows if x[a.column].strip())
    domains, out, bad = Counter(), [], 0
    for ln, row in enumerate(rows, start=2):
        mail = row[a.column].strip()
        if not mail:
            status, hint = "비어 있음", ""
        elif not PATTERN.match(mail):
            status, hint = "형식 오류", ""
        else:
            dom = mail.split("@")[1].lower()
            domains[dom] += 1
            status, hint = "정상", ""
            if dom in TYPOS:
                status, hint = "오타 의심", f"{TYPOS[dom]} 아닌가요?"
            elif seen[mail.lower()] > 1:
                status, hint = "중복", "같은 주소가 여러 번 있음"
        bad += status != "정상"
        out.append({"줄": ln, "이메일": mail, "상태": status, "힌트": hint})

    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.DictWriter(fp, fieldnames=["줄", "이메일", "상태", "힌트"])
        w.writeheader()
        w.writerows(out)
    print(f"전체 {len(out)}건 중 확인 필요 {bad}건 → {a.output}")
    print("도메인별 개수:", ", ".join(f"{d} {n}" for d, n in domains.most_common(5)))


if __name__ == "__main__":
    main()
