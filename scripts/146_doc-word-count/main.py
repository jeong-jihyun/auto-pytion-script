"""폴더 안 문서(txt, md, docx)의 글자 수·단어 수·원고지 매수를 한 번에 세는 스크립트.

생각의 흐름:
  1) 보고서·제안서·자기소개서는 '공백 포함/제외 몇 자', 'A4 몇 쪽', '원고지 몇 매' 같은 분량 제한이 있습니다.
     파일을 하나씩 열어 확인하기 번거롭습니다.
  2) docx 는 사실 zip 파일이고 본문은 word/document.xml 에 있습니다. 표준 라이브러리 zipfile + xml 로
     <w:t> 글자와 문단(<w:p>)을 읽으면 외부 패키지 없이 텍스트를 얻을 수 있습니다.
  3) 파일마다 다음을 셉니다.
       - 공백 포함 글자 수, 공백 제외 글자 수
       - 단어 수(공백 기준), 문단 수(빈 줄 제외)
       - 한글 글자 수 비율
       - 200자 원고지 매수(문단마다 새 줄에서 시작, 한 줄 20칸 → 대략적인 추정)
  4) --limit 을 주면 공백 포함 글자 수가 그보다 많은 파일에 OVER 표시를 합니다.
  5) 결과는 CSV 와 화면 표로 보여 줍니다. 파일은 읽기만 하고 바꾸지 않습니다.
"""
import argparse
import csv
import math
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def read_docx(path):
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    paras = []
    for p in root.iter(W + "p"):
        parts = []
        for node in p.iter():
            if node.tag == W + "t" and node.text:
                parts.append(node.text)
            elif node.tag == W + "tab":
                parts.append("\t")
        paras.append("".join(parts))
    return "\n".join(paras)


def read_text(path):
    for enc in ("utf-8-sig", "cp949"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def manuscript_pages(paragraphs, per_line=20, lines=10):
    """200자 원고지(20칸×10줄) 매수 추정: 문단은 첫 칸 들여쓰기 1칸 + 새 줄 시작."""
    total_lines = sum(math.ceil((len(p) + 1) / per_line) for p in paragraphs)
    return total_lines / lines


def stats(text):
    paragraphs = [p.strip() for p in text.splitlines() if p.strip()]
    no_space = re.sub(r"\s", "", text)
    hangul = len(re.findall(r"[가-힣]", text))
    with_space = len(text.replace("\r", "").replace("\n", ""))
    return {
        "공백포함": with_space,
        "공백제외": len(no_space),
        "단어": len(text.split()),
        "문단": len(paragraphs),
        "한글비율": f"{hangul / len(no_space) * 100:.0f}%" if no_space else "0%",
        "원고지매수": f"{manuscript_pages(paragraphs):.1f}",
    }


def main():
    p = argparse.ArgumentParser(description="문서 글자 수·원고지 매수 집계")
    p.add_argument("folder", help="문서가 있는 폴더")
    p.add_argument("-o", "--output", default="word_count.out.csv")
    p.add_argument("--limit", type=int, default=0, help="공백 포함 글자 수 상한 (넘으면 OVER)")
    p.add_argument("--recursive", action="store_true", help="하위 폴더까지")
    a = p.parse_args()

    folder = Path(a.folder)
    pattern = "**/*" if a.recursive else "*"
    files = sorted(f for f in folder.glob(pattern) if f.is_file() and f.suffix.lower() in (".txt", ".md", ".docx"))
    if not files:
        raise SystemExit("[안내] txt/md/docx 파일이 없습니다.")

    rows = []
    for f in files:
        try:
            text = read_docx(f) if f.suffix.lower() == ".docx" else read_text(f)
        except (zipfile.BadZipFile, KeyError, ET.ParseError) as e:
            print(f"[건너뜀] {f.name}: 읽을 수 없는 docx ({e})")
            continue
        s = stats(text)
        s["파일"] = str(f.relative_to(folder))
        s["판정"] = "OVER" if a.limit and s["공백포함"] > a.limit else ""
        rows.append(s)

    fields = ["파일", "공백포함", "공백제외", "단어", "문단", "한글비율", "원고지매수", "판정"]
    with open(a.output, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    print(f"{'파일':24s} {'공백포함':>8s} {'공백제외':>8s} {'단어':>6s} {'문단':>4s} {'원고지':>6s} 판정")
    for r in rows:
        print(f"{r['파일'][:24]:24s} {r['공백포함']:8,d} {r['공백제외']:8,d} {r['단어']:6,d} {r['문단']:4d} {r['원고지매수']:>6s} {r['판정']}")
    print(f"\n{len(rows)}개 파일 → {a.output}")


if __name__ == "__main__":
    main()
