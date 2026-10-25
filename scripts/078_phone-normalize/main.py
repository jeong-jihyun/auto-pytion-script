"""CSV의 전화번호 형식을 '010-1234-5678'처럼 하나로 통일하는 스크립트.

고객·거래처 목록에는 01012345678, 010.1234.5678, +82 10-1234-5678, (02)123-4567 이 섞여 있습니다.
생각의 흐름:
  1) +82 로 시작하면 0을 붙인 국내 번호로 바꿉니다.
  2) 숫자만 남긴 뒤 앞자리(02, 031~064, 010~019, 070, 080, 15xx/16xx/18xx 대표번호)를 봅니다.
  3) 앞자리 규칙에 맞게 하이픈을 넣습니다. 규칙에 안 맞으면 "확인필요"로 표시하고, 원래 값은 지우지 않습니다.
원래 열은 그대로 두고 '전화_정리', '전화_종류', '전화_점검' 열을 새로 붙입니다.
"""
import argparse
import csv
import re
import sys
from pathlib import Path

AREA = {"02"} | {f"0{n}" for n in (31, 32, 33, 41, 42, 43, 44, 51, 52, 53, 54, 55, 61, 62, 63, 64)}


def normalize(text):
    """(정리된 번호, 종류, 점검) 을 돌려줍니다."""
    raw = (text or "").strip()
    if not raw:
        return "", "", "빈 값"
    s = re.sub(r"(?:내선|ext\.?|#)\s*\d+$", "", raw, flags=re.I).strip()
    if s.startswith("+82"):
        s = "0" + s[3:].lstrip(" -.()0")
    d = re.sub(r"\D", "", s)
    if re.fullmatch(r"01[016789]\d{7,8}", d):
        mid = 3 if len(d) == 10 else 4
        return f"{d[:3]}-{d[3:3 + mid]}-{d[3 + mid:]}", "휴대폰", "정상"
    if re.fullmatch(r"1[568]\d{6}", d):
        return f"{d[:4]}-{d[4:]}", "대표번호", "정상"
    if d.startswith("02") and len(d) in (9, 10):
        mid = len(d) - 6
        return f"02-{d[2:2 + mid]}-{d[2 + mid:]}", "유선", "정상"
    if d[:3] in AREA | {"070", "080"} and len(d) in (10, 11):
        mid = len(d) - 7
        kind = "인터넷전화" if d[:3] == "070" else ("수신자부담" if d[:3] == "080" else "유선")
        return f"{d[:3]}-{d[3:3 + mid]}-{d[3 + mid:]}", kind, "정상"
    return "", "", f"확인필요({len(d)}자리)"


def main():
    p = argparse.ArgumentParser(description="전화번호 형식 통일")
    p.add_argument("input", type=Path)
    p.add_argument("--col", default="전화")
    p.add_argument("-o", "--output", type=Path, default=Path("output/phone_normalized.csv"))
    a = p.parse_args()

    with a.input.open(newline="", encoding="utf-8-sig") as fp:
        r = csv.DictReader(fp)
        fields = list(r.fieldnames or [])
        if a.col not in fields:
            print(f"[오류] 없는 열: {a.col} (있는 열: {fields})")
            sys.exit(1)
        rows = list(r)
    ok = 0
    extra = [f"{a.col}_정리", f"{a.col}_종류", f"{a.col}_점검"]
    for row in rows:
        vals = normalize(row[a.col])
        row.update(dict(zip(extra, vals)))
        ok += vals[2] == "정상"
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.DictWriter(fp, fieldnames=fields + extra)
        w.writeheader()
        w.writerows(rows)
    print(f"전체 {len(rows)}건: 정상 {ok}건, 확인필요·빈값 {len(rows) - ok}건 → {a.output}")


if __name__ == "__main__":
    main()
