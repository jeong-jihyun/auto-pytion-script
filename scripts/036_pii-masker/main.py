"""개인정보 마스킹(가리기) 스크립트.

CSV 를 외부에 공유하거나 테스트에 쓰기 전에, 개인정보 열을 가려서 새 파일로 저장합니다.
  --mask '열이름:종류,열이름:종류'
  종류: phone(전화번호) / email / name(이름) / id(주민번호 형태 숫자) / card(카드번호) / all(전부 *)
이것은 '내 데이터를 보호'하는 용도입니다. 남의 개인정보를 모으는 용도로 쓰지 마세요.
"""
import argparse
import csv
import re
import sys
from pathlib import Path


def mask_phone(v):
    """010-1234-5678 -> 010-****-5678 (앞 번호와 끝 4자리만 보임)"""
    # 맨 앞 숫자 덩어리(지역·통신사 번호)와 끝 4자리는 두고 가운데만 가립니다.
    parts = re.split(r"(\D+)", v)
    nums = [i for i, s in enumerate(parts) if s.isdigit()]
    if len(nums) >= 3:
        for i in nums[1:-1]:
            parts[i] = "*" * len(parts[i])
        return "".join(parts)
    digits = list(v)
    idx = [i for i, c in enumerate(digits) if c.isdigit()]
    for i in idx[3:-4]:
        digits[i] = "*"
    return "".join(digits)


def mask_email(v):
    """abcdef@site.com -> a*****@site.com"""
    if "@" not in v:
        return "*" * len(v)
    user, dom = v.split("@", 1)
    return user[:1] + "*" * max(len(user) - 1, 1) + "@" + dom


def mask_name(v):
    """홍길동 -> 홍*동, 두 글자는 홍*"""
    if len(v) <= 1:
        return v
    if len(v) == 2:
        return v[0] + "*"
    return v[0] + "*" * (len(v) - 2) + v[-1]


def mask_id(v):
    """주민번호 형태: 앞 6자리만 두고 나머지는 *"""
    digits = re.sub(r"\D", "", v)
    return digits[:6] + "-*******" if len(digits) >= 6 else "*" * len(v)


def mask_card(v):
    """카드번호: 끝 4자리만 보임"""
    digits = re.sub(r"\D", "", v)
    return "****-****-****-" + digits[-4:] if len(digits) >= 4 else "*" * len(v)


MASKERS = {"phone": mask_phone, "email": mask_email, "name": mask_name,
           "id": mask_id, "card": mask_card, "all": lambda v: "*" * len(v)}


def main():
    p = argparse.ArgumentParser(description="CSV 개인정보 마스킹")
    p.add_argument("input", type=Path)
    p.add_argument("--mask", required=True, help="'열:종류,열:종류'")
    p.add_argument("-o", "--output", type=Path, default=Path("output/masked.csv"))
    a = p.parse_args()

    rules = {}
    for item in a.mask.split(","):
        col, _, kind = item.partition(":")
        if kind.strip() not in MASKERS:
            sys.exit(f"[오류] 알 수 없는 종류 '{kind}' (가능: {', '.join(MASKERS)})")
        rules[col.strip()] = MASKERS[kind.strip()]

    with a.input.open(newline="", encoding="utf-8-sig") as fp:
        r = csv.DictReader(fp)
        header = r.fieldnames or []
        rows = list(r)
    for col in rules:
        if col not in header:
            sys.exit(f"[오류] '{col}' 열이 없습니다. 있는 열: {header}")
    for row in rows:
        for col, fn in rules.items():
            row[col] = fn((row[col] or "").strip())
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.DictWriter(fp, fieldnames=header)
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)}행, {len(rules)}개 열을 가렸습니다 -> {a.output}")


if __name__ == "__main__":
    main()
