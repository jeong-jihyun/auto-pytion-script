"""폴더 안 이미지(영수증 사진, 스캔본)를 이름 순서대로 PDF 한 파일로 묶는 스크립트.

생각의 흐름:
  1) 영수증·증빙을 휴대폰으로 찍으면 jpg 여러 장이 생깁니다. 제출할 때는 PDF 한 파일이 편합니다.
  2) 이미지를 '사람이 생각하는 이름 순서'로 줄 세웁니다. (img2 가 img10 보다 앞에 오도록 숫자는 숫자로 비교)
  3) 휴대폰 사진은 EXIF 회전 정보가 있어서 그대로 넣으면 옆으로 눕습니다. 회전 정보를 반영해 바로 세웁니다.
  4) 투명 배경(PNG)은 PDF에 그대로 못 넣으니 흰 바탕에 얹어 RGB로 바꿉니다.
  5) --page a4 를 주면 A4 종이 안에 여백을 두고 비율을 지켜 가운데 배치합니다(인쇄용).
     기본(--page original)은 이미지 크기 그대로 한 장씩 만듭니다.
  6) 같은 이름의 PDF가 이미 있으면 덮어쓰지 않고 멈춥니다(--overwrite 로만 덮어씀).
"""
import argparse
import re
import sys
from pathlib import Path

from PIL import Image, ImageOps

EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff", ".webp"}
A4_PX = (1240, 1754)  # 150dpi 기준 A4 (210×297mm)


def natural_key(path):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", path.name)]


def to_rgb(img):
    img = ImageOps.exif_transpose(img)
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        bg = Image.new("RGB", img.size, "white")
        bg.paste(img, mask=img.split()[-1])
        return bg
    return img.convert("RGB")


def fit_a4(img, margin):
    page = Image.new("RGB", A4_PX, "white")
    box = (A4_PX[0] - 2 * margin, A4_PX[1] - 2 * margin)
    im = img.copy()
    im.thumbnail(box)  # 비율 유지하며 줄이기(키우지는 않음)
    page.paste(im, ((A4_PX[0] - im.width) // 2, (A4_PX[1] - im.height) // 2))
    return page


def main():
    p = argparse.ArgumentParser(description="이미지 여러 장 → PDF 한 파일")
    p.add_argument("folder", type=Path, help="이미지 폴더")
    p.add_argument("-o", "--output", type=Path, default=Path("output/images.pdf"))
    p.add_argument("--page", choices=["original", "a4"], default="original", help="쪽 크기(기본 이미지 그대로)")
    p.add_argument("--margin", type=int, default=60, help="A4일 때 여백(px, 기본 60)")
    p.add_argument("--overwrite", action="store_true", help="같은 이름 PDF가 있어도 덮어씀")
    a = p.parse_args()

    files = sorted([f for f in a.folder.iterdir() if f.suffix.lower() in EXTS], key=natural_key)
    if not files:
        sys.exit(f"이미지가 없습니다: {a.folder}")
    if a.output.exists() and not a.overwrite:
        sys.exit(f"이미 있는 파일이라 멈춥니다(덮어쓰려면 --overwrite): {a.output}")

    pages, skipped = [], []
    for f in files:
        try:
            with Image.open(f) as im:
                im = to_rgb(im)
                pages.append(fit_a4(im, a.margin) if a.page == "a4" else im)
            print(f"  {len(pages):>3}쪽: {f.name} ({pages[-1].width}x{pages[-1].height})")
        except Exception as e:
            skipped.append((f.name, e))
    if not pages:
        sys.exit("열 수 있는 이미지가 없습니다.")
    a.output.parent.mkdir(parents=True, exist_ok=True)
    pages[0].save(a.output, "PDF", resolution=150, save_all=True, append_images=pages[1:])
    for name, e in skipped:
        print(f"  [건너뜀] {name}: {e}")
    print(f"PDF 완성: {a.output} ({len(pages)}쪽, {a.output.stat().st_size / 1024:.1f}KB)")


if __name__ == "__main__":
    main()
