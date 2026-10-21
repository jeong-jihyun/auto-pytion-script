"""워드(docx) 문서에서 글자를 뽑는 스크립트.

docx 는 사실 zip 파일이라서, 표준 라이브러리(zipfile)만으로 본문 글자를 읽습니다.
문단과 표의 글자를 txt 로 저장하고, --find 로 찾을 낱말이 몇 번 나오는지도 셉니다.
(머리글·바닥글·텍스트 상자는 읽지 않습니다.)
"""
import argparse
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def para_text(p):
    """문단(w:p) 하나의 글자를 이어 붙입니다. 탭·줄바꿈도 반영."""
    out = []
    for el in p.iter():
        if el.tag == W + "t":
            out.append(el.text or "")
        elif el.tag == W + "tab":
            out.append("\t")
        elif el.tag in (W + "br", W + "cr"):
            out.append("\n")
    return "".join(out)


def extract(path):
    """본문을 위에서 아래 순서로 줄 목록으로 돌려줍니다. 표의 한 행은 ' | ' 로 연결."""
    with zipfile.ZipFile(path) as z:
        if "word/document.xml" not in z.namelist():
            raise SystemExit("오류: 워드(docx) 문서가 아닙니다.")
        root = ET.fromstring(z.read("word/document.xml"))
    body = root.find(W + "body")
    lines = []
    for child in body:
        if child.tag == W + "p":
            lines.append(para_text(child))
        elif child.tag == W + "tbl":
            for tr in child.iter(W + "tr"):
                cells = ["".join(para_text(p) for p in tc.iter(W + "p")) for tc in tr.findall(W + "tc")]
                lines.append(" | ".join(cells))
    return lines


def main():
    p = argparse.ArgumentParser(description="docx 글자 추출")
    p.add_argument("input", type=Path)
    p.add_argument("-o", "--output", type=Path, default=Path("output/docx_text.txt"))
    p.add_argument("--find", action="append", default=[], help="세어 볼 낱말 (여러 번 지정 가능)")
    a = p.parse_args()

    lines = extract(a.input)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    text = "\n".join(lines)
    chars = len(re.sub(r"\s", "", text))
    print(f"{len(lines)}줄, {chars}글자(공백 제외) -> {a.output}")
    for word in a.find:
        print(f"  '{word}': {text.count(word)}번")


if __name__ == "__main__":
    main()
