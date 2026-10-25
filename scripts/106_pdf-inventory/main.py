"""폴더 안 PDF들의 쪽수·크기·암호 여부·제목·글자 유무를 한 표로 정리하는 스크립트.

생각의 흐름:
  1) 폴더(하위 포함 선택)의 PDF를 하나씩 엽니다. 깨진 파일은 '열기 실패'로 적고 다음으로 넘어갑니다.
  2) 쪽수, 파일 크기, 암호 걸림 여부, 문서 정보(제목·작성 프로그램)를 읽습니다.
  3) 첫 몇 쪽에서 글자를 뽑아 보고, 글자가 거의 없으면 '스캔본(이미지) 의심'으로 표시합니다.
     → 검색이 안 되는 PDF를 골라 OCR 할 대상을 정할 수 있습니다.
  4) 마지막에 총 파일 수, 총 쪽수(인쇄량 예상), 암호 파일 수를 요약합니다.
"""
import argparse
import csv
from pathlib import Path

import logging

from pypdf import PdfReader

logging.getLogger("pypdf").setLevel(logging.ERROR)  # 깨진 파일 경고 줄이기


def main():
    p = argparse.ArgumentParser(description="PDF 목록·쪽수 정리")
    p.add_argument("folder", type=Path)
    p.add_argument("--recursive", action="store_true")
    p.add_argument("--check-pages", type=int, default=2, help="글자 유무를 볼 앞쪽 수")
    p.add_argument("--min-chars", type=int, default=20, help="이보다 글자가 적으면 스캔본 의심")
    p.add_argument("-o", "--output", type=Path, default=Path("output/pdf_inventory.csv"))
    a = p.parse_args()

    walker = a.folder.rglob("*") if a.recursive else a.folder.iterdir()
    files = sorted(f for f in walker if f.is_file() and f.suffix.lower() == ".pdf")  # .PDF 대문자도 포함
    rows, total_pages, locked = [], 0, 0
    for f in files:
        size_kb = round(f.stat().st_size / 1024, 1)
        try:
            r = PdfReader(str(f))
            enc = r.is_encrypted
            if enc:
                locked += 1
                ok = False
                try:
                    ok = bool(r.decrypt(""))  # 열기 암호 없이 권한만 걸린 경우
                except Exception:
                    pass
                if not ok:
                    rows.append([str(f.relative_to(a.folder)), size_kb, "", "예", "", "", "", "암호 필요"])
                    continue
            n = len(r.pages)
            total_pages += n
            info = r.metadata or {}
            chars = sum(len((r.pages[i].extract_text() or "").strip()) for i in range(min(n, a.check_pages)))
            kind = "글자 있음" if chars >= a.min_chars else "스캔본(이미지) 의심"
            rows.append([str(f.relative_to(a.folder)), size_kb, n, "예" if enc else "아니오",
                         (info.get("/Title") or ""), (info.get("/Producer") or ""), kind, ""])
        except Exception as e:
            rows.append([str(f.relative_to(a.folder)), size_kb, "", "", "", "", "", f"열기 실패: {type(e).__name__}"])
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["파일", "크기KB", "쪽수", "암호", "제목", "만든프로그램", "글자", "비고"])
        w.writerows(rows)
    print(f"PDF {len(rows)}개, 총 {total_pages}쪽, 암호 {locked}개 → {a.output}")
    for x in rows:
        print(f"  - {x[0]}: {x[2] or '-'}쪽 {x[1]}KB " + " ".join(v for v in (x[6], x[7]) if v))


if __name__ == "__main__":
    main()
