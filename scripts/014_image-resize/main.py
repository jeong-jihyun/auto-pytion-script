"""이미지 일괄 리사이즈 스크립트.

폴더 안의 이미지(jpg, png 등)를 지정한 크기 안에 들어오도록 비율을 유지한 채 줄입니다.
- 원본은 건드리지 않고, 결과를 다른 폴더에 저장합니다.
- 이미 작은 이미지는 키우지 않고 그대로 복사합니다(화질 보호).
- 기본은 미리보기(dry-run). --apply 를 붙여야 실제로 저장합니다.
외부 패키지: Pillow (requirements.txt 참고)
"""
import argparse
import sys
from pathlib import Path

from PIL import Image, ImageOps

확장자들 = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp"}


def main():
    p = argparse.ArgumentParser(description="이미지 일괄 리사이즈")
    p.add_argument("input", help="이미지가 든 폴더")
    p.add_argument("-o", "--output", default="output/resized", help="저장 폴더")
    p.add_argument("--max-width", type=int, default=800, help="최대 가로(픽셀)")
    p.add_argument("--max-height", type=int, default=800, help="최대 세로(픽셀)")
    p.add_argument("--quality", type=int, default=85, help="JPG 화질 1~95")
    p.add_argument("--apply", action="store_true", help="실제로 저장 (없으면 미리보기만)")
    a = p.parse_args()

    입력 = Path(a.input)
    출력 = Path(a.output)
    파일들 = sorted(f for f in 입력.iterdir() if f.suffix.lower() in 확장자들)
    if not 파일들:
        print("이미지 파일이 없습니다.")
        return 1
    if not a.apply:
        print("[미리보기] 실제로 저장하지 않습니다. 저장하려면 --apply 를 붙이세요.")
    else:
        출력.mkdir(parents=True, exist_ok=True)

    줄임수 = 0
    for f in 파일들:
        try:
            with Image.open(f) as 그림:
                그림 = ImageOps.exif_transpose(그림)  # 휴대폰 사진의 회전 정보 반영
                w, h = 그림.size
                비율 = min(a.max_width / w, a.max_height / h, 1.0)  # 1.0이면 키우지 않음
                새크기 = (max(1, round(w * 비율)), max(1, round(h * 비율)))
                상태 = "줄임" if 비율 < 1.0 else "그대로"
                print(f"  {f.name}: {w}x{h} -> {새크기[0]}x{새크기[1]} ({상태})")
                if 비율 < 1.0:
                    줄임수 += 1
                if a.apply:
                    결과 = 그림.resize(새크기, Image.LANCZOS) if 비율 < 1.0 else 그림
                    저장옵션 = {}
                    if f.suffix.lower() in (".jpg", ".jpeg"):
                        결과 = 결과.convert("RGB")
                        저장옵션 = {"quality": a.quality, "optimize": True}
                    결과.save(출력 / f.name, **저장옵션)
        except Exception as e:
            print(f"  [건너뜀] {f.name}: 열 수 없어요 ({e})")
    print(f"끝: 전체 {len(파일들)}개 중 {줄임수}개를 줄였습니다." + (f" -> {출력}" if a.apply else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
