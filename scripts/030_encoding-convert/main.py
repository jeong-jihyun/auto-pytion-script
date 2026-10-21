"""텍스트 파일 인코딩 변환 스크립트 (cp949 <-> utf-8).

엑셀·구형 시스템에서 받은 CSV/TXT 가 한글이 깨져 보일 때 씁니다.
폴더 안의 파일을 읽어 원래 인코딩을 알아내고(utf-8 -> cp949 순서로 시도),
--to 로 정한 인코딩으로 '새 폴더에' 저장합니다. 원본은 건드리지 않습니다.
기본은 미리보기(dry-run)이고 --apply 를 붙여야 파일을 만듭니다.
"""
import argparse
from pathlib import Path


def detect(raw):
    """바이트가 utf-8 이면 'utf-8', 아니면 cp949 로 읽어 보고 안 되면 None."""
    for enc in ("utf-8-sig", "cp949"):
        try:
            raw.decode(enc)
            return enc
        except UnicodeDecodeError:
            continue
    return None


def main():
    p = argparse.ArgumentParser(description="텍스트 파일 인코딩 변환")
    p.add_argument("folder", type=Path)
    p.add_argument("--to", choices=["utf-8", "cp949"], default="utf-8", help="바꿀 인코딩 (기본 utf-8)")
    p.add_argument("--pattern", default="*.csv", help="대상 파일 패턴 (기본 *.csv)")
    p.add_argument("-o", "--output", type=Path, default=Path("converted_out"))
    p.add_argument("--apply", action="store_true", help="실제로 파일을 만듦 (없으면 미리보기)")
    a = p.parse_args()
    if not a.folder.is_dir():
        raise SystemExit(f"오류: 폴더가 아닙니다: {a.folder}")

    done = skipped = failed = 0
    for f in sorted(a.folder.glob(a.pattern)):
        if not f.is_file():
            continue
        raw = f.read_bytes()
        src = detect(raw)
        if src is None:
            print(f"  [실패] {f.name}: utf-8 도 cp949 도 아닙니다.")
            failed += 1
            continue
        if src.startswith("utf-8") and a.to == "utf-8" and not raw.startswith(b"\xef\xbb\xbf"):
            print(f"  [건너뜀] {f.name}: 이미 utf-8 입니다.")
            skipped += 1
            continue
        text = raw.decode(src)
        try:
            new = text.encode("utf-8-sig" if a.to == "utf-8" else "cp949")
        except UnicodeEncodeError:
            print(f"  [실패] {f.name}: cp949 로 표현할 수 없는 글자가 있습니다.")
            failed += 1
            continue
        print(f"  [{'변환' if a.apply else '대상'}] {f.name}: {src} -> {a.to}")
        if a.apply:
            a.output.mkdir(parents=True, exist_ok=True)
            (a.output / f.name).write_bytes(new)
        done += 1
    mode = "저장 완료" if a.apply else "미리보기(--apply 로 실행)"
    print(f"변환 대상 {done}개, 건너뜀 {skipped}개, 실패 {failed}개 - {mode}")


if __name__ == "__main__":
    main()
