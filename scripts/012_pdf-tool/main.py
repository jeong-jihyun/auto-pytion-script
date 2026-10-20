"""PDF 병합·분할·텍스트 추출 스크립트.

세 가지 일을 합니다.
  merge : 여러 PDF를 이름순으로 하나로 합칩니다.
  split : PDF 한 개를 N쪽씩 또는 지정한 쪽 범위별로 나눕니다.
  text  : PDF의 글자를 txt로 뽑습니다. (스캔 이미지 PDF는 글자가 없어서 뽑히지 않습니다)
외부 패키지: pypdf (requirements.txt 참고)
"""
import argparse
import sys
from pathlib import Path

from pypdf import PdfReader, PdfWriter


def 범위_해석(글, 전체쪽수):
    """'1-2,3,5-' 같은 글을 [(시작, 끝), ...] (1부터, 끝 포함)로 바꿉니다."""
    결과 = []
    for 조각 in 글.split(","):
        조각 = 조각.strip()
        if not 조각:
            continue
        앞, _, 뒤 = 조각.partition("-")
        시작 = int(앞)
        끝 = 시작 if "-" not in 조각 else (int(뒤) if 뒤 else 전체쪽수)
        if not (1 <= 시작 <= 끝 <= 전체쪽수):
            raise ValueError(f"쪽 범위가 올바르지 않습니다: {조각} (전체 {전체쪽수}쪽)")
        결과.append((시작, 끝))
    return 결과


def 병합(a):
    입력 = Path(a.input)
    파일들 = sorted(입력.glob("*.pdf")) if 입력.is_dir() else [입력]
    out = Path(a.output)
    파일들 = [f for f in 파일들 if f.resolve() != out.resolve()]
    if not 파일들:
        print("합칠 PDF가 없습니다.")
        return 1
    w = PdfWriter()
    for f in 파일들:
        r = PdfReader(str(f))
        for 쪽 in r.pages:
            w.add_page(쪽)
        print(f"  추가: {f.name} ({len(r.pages)}쪽)")
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("wb") as fp:
        w.write(fp)
    print(f"완료: {len(파일들)}개 -> {out} (총 {len(w.pages)}쪽)")
    return 0


def 분할(a):
    r = PdfReader(a.input)
    전체 = len(r.pages)
    if a.ranges:
        구간들 = 범위_해석(a.ranges, 전체)
    else:
        n = a.pages_per_file
        구간들 = [(s, min(s + n - 1, 전체)) for s in range(1, 전체 + 1, n)]
    outdir = Path(a.output)
    outdir.mkdir(parents=True, exist_ok=True)
    기본이름 = Path(a.input).stem
    for i, (s, e) in enumerate(구간들, start=1):
        w = PdfWriter()
        for 번호 in range(s, e + 1):
            w.add_page(r.pages[번호 - 1])
        경로 = outdir / f"{기본이름}_part{i:02d}_p{s}-{e}.pdf"
        with 경로.open("wb") as fp:
            w.write(fp)
        print(f"  만듦: {경로.name} ({e - s + 1}쪽)")
    print(f"완료: 전체 {전체}쪽을 {len(구간들)}개로 나눴습니다 -> {outdir}")
    return 0


def 글자뽑기(a):
    r = PdfReader(a.input)
    조각 = []
    빈쪽 = 0
    for i, 쪽 in enumerate(r.pages, start=1):
        글 = (쪽.extract_text() or "").strip()
        if not 글:
            빈쪽 += 1
        조각.append(f"===== {i}쪽 =====\n{글}\n")
    out = Path(a.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(조각), encoding="utf-8")
    print(f"완료: {len(r.pages)}쪽 -> {out}")
    if 빈쪽:
        print(f"[알림] 글자가 없는 쪽이 {빈쪽}개 있어요. 스캔 이미지일 수 있습니다(OCR은 이 스크립트에 없음).")
    return 0


def main():
    p = argparse.ArgumentParser(description="PDF 병합·분할·텍스트 추출")
    sub = p.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("merge", help="PDF 합치기")
    m.add_argument("input", help="PDF가 든 폴더(또는 PDF 파일 1개)")
    m.add_argument("-o", "--output", default="output/merged.pdf")
    m.set_defaults(func=병합)
    s = sub.add_parser("split", help="PDF 나누기")
    s.add_argument("input", help="나눌 PDF")
    s.add_argument("-o", "--output", default="output/split", help="결과를 넣을 폴더")
    g = s.add_mutually_exclusive_group()
    g.add_argument("--pages-per-file", type=int, default=1, help="N쪽씩 나누기(기본 1)")
    g.add_argument("--ranges", help="쪽 범위 예: 1-2,3,5-")
    s.set_defaults(func=분할)
    t = sub.add_parser("text", help="글자 뽑기")
    t.add_argument("input")
    t.add_argument("-o", "--output", default="output/text.txt")
    t.set_defaults(func=글자뽑기)
    a = p.parse_args()
    try:
        return a.func(a)
    except Exception as e:  # 깨진 PDF, 잘못된 범위 등을 알기 쉽게 알려 줍니다.
        print(f"[오류] {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
