"""연락처 CSV를 휴대폰·메일 프로그램에서 가져올 수 있는 vCard(.vcf) 파일로 바꾸는 스크립트.

생각의 흐름:
  1) CSV(이름,전화,이메일,회사)를 한 줄씩 읽어 vCard 3.0 형식 한 건으로 만듭니다.
  2) 세미콜론·쉼표·줄바꿈은 vCard 에서 특별한 글자라서 백슬래시로 막아 줍니다.
  3) 이름이 없는 줄은 건너뛰고 몇 건을 건너뛰었는지 알려 줍니다.
  4) 모두 하나의 .vcf 파일에 이어 붙입니다(대부분의 앱이 한 번에 가져옵니다).
"""
import argparse
import csv
from pathlib import Path


def esc(text):
    return (text or "").strip().replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def card(r):
    lines = ["BEGIN:VCARD", "VERSION:3.0", f"FN:{esc(r['이름'])}", f"N:{esc(r['이름'])};;;;"]
    if r.get("회사", "").strip():
        lines.append(f"ORG:{esc(r['회사'])}")
    if r.get("전화", "").strip():
        lines.append(f"TEL;TYPE=CELL:{esc(r['전화'])}")
    if r.get("이메일", "").strip():
        lines.append(f"EMAIL;TYPE=INTERNET:{esc(r['이메일'])}")
    lines.append("END:VCARD")
    return "\r\n".join(lines) + "\r\n"


def main():
    p = argparse.ArgumentParser(description="CSV -> vCard")
    p.add_argument("--input", required=True, help="CSV(이름,전화,이메일,회사)")
    p.add_argument("--out", default="output/연락처.vcf")
    a = p.parse_args()
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    made = skipped = 0
    with open(a.input, encoding="utf-8-sig", newline="") as f, open(out, "w", encoding="utf-8", newline="") as o:
        for r in csv.DictReader(f):
            if not (r.get("이름") or "").strip():
                skipped += 1
                continue
            o.write(card(r))
            made += 1
    print(f"완료: {made}명 만듦, 이름 없어 건너뜀 {skipped}건 -> {out}")


if __name__ == "__main__":
    main()
