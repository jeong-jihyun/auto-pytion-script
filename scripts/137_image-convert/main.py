"""폴더 안 이미지를 다른 형식(jpg/png/webp)으로 한꺼번에 바꾸는 스크립트.

생각의 흐름:
  1) 업무 시스템·메일·문서에 올릴 때 'PNG는 안 되고 JPG만', '용량을 줄이려 WEBP로' 같은 요구가 자주 있습니다.
  2) 폴더를 돌며 지정한 확장자(--from)의 이미지를 열어 --to 형식으로 저장합니다.
  3) 형식을 바꿀 때 생기는 함정을 미리 처리합니다.
       - JPG는 투명(알파) 채널이 없어서 투명 부분이 검게 변합니다 → 흰 배경(--bg)을 깔고 합칩니다.
       - 팔레트(P) 이미지, 흑백(L) 이미지도 RGB로 바꿔 저장합니다.
       - 휴대폰 사진은 EXIF 회전 정보가 있어서, 회전 정보대로 바로 세운 뒤 저장합니다.
  4) 안전을 위해
       - 기본은 미리보기(dry-run): 무엇을 만들지 목록만 보여 줍니다. --apply 를 붙여야 실제로 저장합니다.
       - 원본은 절대 지우거나 덮어쓰지 않고, 결과는 출력 폴더에 하위 폴더 구조를 유지해 저장합니다.
       - 출력 파일이 이미 있으면 건너뜁니다(--overwrite 로만 덮어씀).
  5) 끝나면 원본·결과 용량 합계를 보여 줘서 얼마나 줄었는지 알 수 있게 합니다.
"""
import argparse
from pathlib import Path

from PIL import Image, ImageOps

FMT = {"jpg": "JPEG", "jpeg": "JPEG", "png": "PNG", "webp": "WEBP"}


def to_rgb(img, bg):
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        img = img.convert("RGBA")
        base = Image.new("RGB", img.size, bg)
        base.paste(img, mask=img.split()[-1])
        return base
    return img.convert("RGB")


def main():
    p = argparse.ArgumentParser(description="이미지 형식 일괄 변환")
    p.add_argument("src", type=Path, help="원본 폴더")
    p.add_argument("--to", required=True, choices=["jpg", "png", "webp"], help="바꿀 형식")
    p.add_argument("--from", dest="src_ext", default="png,jpg,jpeg,bmp,gif,webp,tif,tiff",
                   help="대상 확장자, 쉼표로(기본: 흔한 이미지 전부)")
    p.add_argument("-o", "--output", type=Path, default=Path("converted_out"), help="출력 폴더")
    p.add_argument("--quality", type=int, default=85, help="jpg/webp 품질 1~95(기본 85)")
    p.add_argument("--bg", default="white", help="투명 부분을 채울 배경색(jpg 변환 시, 기본 white)")
    p.add_argument("--apply", action="store_true", help="실제로 저장(없으면 미리보기)")
    p.add_argument("--overwrite", action="store_true", help="출력 파일이 있으면 덮어씀")
    a = p.parse_args()

    exts = {"." + e.strip().lower().lstrip(".") for e in a.src_ext.split(",") if e.strip()}
    files = sorted(f for f in a.src.rglob("*") if f.is_file() and f.suffix.lower() in exts)
    out_root = a.output.resolve()
    files = [f for f in files if out_root not in f.resolve().parents]   # 출력 폴더 안 파일은 다시 변환하지 않음
    if not files:
        print("변환할 이미지가 없습니다")
        return

    done = skip = fail = 0
    size_in = size_out = 0
    for f in files:
        rel = f.relative_to(a.src).with_suffix("." + a.to)
        dst = a.output / rel
        if f.suffix.lower().lstrip(".") in ({a.to} | ({"jpeg"} if a.to == "jpg" else set())):
            print(f"  건너뜀(이미 {a.to}): {f}")
            skip += 1
            continue
        if dst.exists() and not a.overwrite:
            print(f"  건너뜀(이미 있음): {dst}")
            skip += 1
            continue
        if not a.apply:
            print(f"  [미리보기] {f} → {dst}")
            done += 1
            continue
        try:
            with Image.open(f) as img:
                img = ImageOps.exif_transpose(img)   # 휴대폰 사진 회전 바로잡기
                if a.to == "jpg":
                    img = to_rgb(img, a.bg)
                elif img.mode == "P" and a.to == "webp":
                    img = img.convert("RGBA")
                dst.parent.mkdir(parents=True, exist_ok=True)
                opts = {"quality": a.quality} if a.to in ("jpg", "webp") else {"optimize": True}
                img.save(dst, FMT[a.to], **opts)
            size_in += f.stat().st_size
            size_out += dst.stat().st_size
            print(f"  변환: {f} → {dst}")
            done += 1
        except Exception as e:  # 깨진 파일이 있어도 나머지는 계속합니다
            print(f"  [실패] {f}: {e}")
            fail += 1

    mode = "변환" if a.apply else "변환 예정"
    print(f"{mode} {done}개, 건너뜀 {skip}개, 실패 {fail}개")
    if a.apply and size_in:
        print(f"용량: 원본 {size_in / 1024:,.1f}KB → 결과 {size_out / 1024:,.1f}KB ({size_out / size_in:.0%})")
    if not a.apply:
        print("실제로 저장하려면 --apply 를 붙이세요")


if __name__ == "__main__":
    main()
