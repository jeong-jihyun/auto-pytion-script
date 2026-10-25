"""폴더 안 이미지에 '대외비', '회사명 © 2026' 같은 글자 워터마크를 한꺼번에 넣는 스크립트.

생각의 흐름:
  1) 원본은 절대 덮어쓰지 않습니다. 결과는 --outdir 에 같은 이름으로 저장합니다.
  2) 기본은 미리보기(--apply 없으면 어떤 파일을 어떻게 만들지 목록만 출력)입니다.
  3) 글자 크기는 이미지 짧은 변의 비율(--size 0.05 = 5%)로 정해, 큰 사진·작은 캡처 모두 비슷하게 보이게 합니다.
  4) 위치는 오른쪽아래(br)·가운데(center)·바둑판 반복(tile) 중 고릅니다.
     tile 은 글자를 비스듬히 여러 번 깔아 잘라내기 어렵게 합니다.
  5) 한글 글꼴은 --font 로 지정합니다. 없으면 흔한 위치에서 찾아보고, 그래도 없으면 기본 글꼴(한글 깨짐 가능)을 씁니다.
"""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
FONT_CANDIDATES = [
    "C:/Windows/Fonts/malgun.ttf",
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
]


def find_font(path, size):
    for cand in ([path] if path else []) + FONT_CANDIDATES:
        if cand and Path(cand).exists():
            return ImageFont.truetype(cand, size)
    print("  ! 한글 글꼴을 찾지 못해 기본 글꼴을 씁니다(한글이 네모로 보일 수 있음). --font 로 지정하세요.")
    return ImageFont.load_default()


def stamp(img, text, font, where, opacity, margin):
    base = img.convert("RGBA")
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    l, t, r, b = d.textbbox((0, 0), text, font=font)
    tw, th = r - l, b - t
    fill = (255, 255, 255, int(255 * opacity))
    shadow = (0, 0, 0, int(255 * opacity * 0.6))
    W, H = base.size
    if where == "tile":
        tile = Image.new("RGBA", (tw + margin * 4, th + margin * 4), (0, 0, 0, 0))
        td = ImageDraw.Draw(tile)
        td.text((margin * 2 - l, margin * 2 - t), text, font=font, fill=fill)
        tile = tile.rotate(30, expand=True)
        for row, y in enumerate(range(0, H, tile.height)):
            start = -tile.width // 2 if row % 2 else 0  # 줄마다 반 칸씩 엇갈리게
            for x in range(start, W, tile.width):
                layer.paste(tile, (x, y), tile)  # paste 는 음수 좌표(가장자리 잘림)도 됩니다
    else:
        if where == "center":
            x, y = (W - tw) // 2, (H - th) // 2
        else:  # br
            x, y = W - tw - margin, H - th - margin
        d.text((x - l + 2, y - t + 2), text, font=font, fill=shadow)
        d.text((x - l, y - t), text, font=font, fill=fill)
    out = Image.alpha_composite(base, layer)
    return out if img.mode == "RGBA" else out.convert("RGB")


def main():
    p = argparse.ArgumentParser(description="이미지 글자 워터마크 일괄 넣기")
    p.add_argument("src", type=Path, help="이미지 폴더")
    p.add_argument("--text", required=True, help="넣을 글자(예: 대외비)")
    p.add_argument("--outdir", type=Path, default=Path("output/watermarked"))
    p.add_argument("--where", choices=["br", "center", "tile"], default="br")
    p.add_argument("--size", type=float, default=0.05, help="글자 높이 = 짧은 변 × 비율")
    p.add_argument("--opacity", type=float, default=0.5, help="0~1, 클수록 진함")
    p.add_argument("--font", default="", help="글꼴 파일 경로(.ttf/.ttc)")
    p.add_argument("--apply", action="store_true", help="실제로 저장(없으면 미리보기)")
    a = p.parse_args()

    files = sorted(f for f in a.src.iterdir() if f.suffix.lower() in EXTS)
    if a.outdir.resolve() == a.src.resolve():
        raise SystemExit("출력 폴더가 원본 폴더와 같습니다. 원본 보호를 위해 다른 폴더를 지정하세요.")
    print(f"이미지 {len(files)}개, 글자 '{a.text}', 위치 {a.where} ({'저장' if a.apply else '미리보기'})")
    if a.apply:
        a.outdir.mkdir(parents=True, exist_ok=True)
    done = 0
    for f in files:
        with Image.open(f) as img:
            size = max(12, int(min(img.size) * a.size))
            target = a.outdir / f.name
            print(f"  - {f.name} {img.size[0]}x{img.size[1]} → {target} (글자 {size}px)")
            if not a.apply:
                continue
            font = find_font(a.font, size)
            out = stamp(img, a.text, font, a.where, a.opacity, max(8, size // 2))
            out.save(target, quality=92) if f.suffix.lower() in (".jpg", ".jpeg") else out.save(target)
            done += 1
    if not a.apply:
        print("미리보기입니다. 실제로 저장하려면 --apply 를 붙이세요.")
    else:
        print(f"완료: {done}개 저장 → {a.outdir}")


if __name__ == "__main__":
    main()
