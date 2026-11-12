"""맥(macOS)에서 받은 파일 이름의 한글이 'ㅎㅏㄴㄱㅡㄹ'처럼 자모로 갈라져 보이는 문제(NFD)를
윈도우·리눅스에서 쓰는 모양(NFC)으로 한꺼번에 고치는 스크립트.

생각의 흐름:
  1) 맥은 파일 이름을 '풀어 쓴' 유니코드(NFD)로 저장하는 경우가 많습니다.
     그 파일을 zip·USB·클라우드로 윈도우에 옮기면 '보고서'가 'ㅂㅗㄱㅗㅅㅓ'처럼 보이고,
     검색이나 같은 이름 비교가 안 됩니다.
  2) 파이썬 unicodedata.normalize('NFC', 이름) 으로 '모아 쓴' 모양으로 바꿀 수 있습니다.
  3) 폴더 안 파일·하위 폴더 이름을 모두 훑어 NFC와 다른 이름만 고릅니다.
     하위 폴더 이름을 먼저 바꾸면 그 안쪽 경로가 달라지므로, 가장 깊은 곳부터 바꿉니다.
  4) 바꾼 이름이 이미 있는 이름과 겹치면 덮어쓰지 않고 건너뜁니다.
  5) 기본은 미리보기(dry-run)이고, --apply 를 붙여야 실제로 이름을 바꿉니다.
"""
import argparse
import os
import unicodedata


def main():
    ap = argparse.ArgumentParser(description="한글 파일 이름 자모 분리(NFD) → NFC 일괄 변환")
    ap.add_argument("folder", help="검사할 폴더")
    ap.add_argument("--apply", action="store_true", help="실제로 이름을 바꿉니다(없으면 미리보기)")
    ap.add_argument("--no-recursive", action="store_true", help="하위 폴더는 보지 않습니다")
    args = ap.parse_args()

    targets = []   # (깊이, 부모경로, 옛이름, 새이름)
    for root, dirs, files in os.walk(args.folder):
        for name in dirs + files:
            new = unicodedata.normalize("NFC", name)
            if new != name:
                depth = os.path.join(root, name).count(os.sep)
                targets.append((depth, root, name, new))
        if args.no_recursive:
            break

    if not targets:
        print("바꿀 이름이 없습니다. 모두 NFC 모양입니다.")
        return

    # 깊은 곳부터 바꿔야 상위 폴더 이름 변경이 하위 경로를 깨뜨리지 않습니다
    targets.sort(key=lambda x: -x[0])
    done = skipped = 0
    print(("[실행]" if args.apply else "[미리보기]") + f" 바꿀 대상 {len(targets)}개")
    for _, root, old, new in targets:
        src, dst = os.path.join(root, old), os.path.join(root, new)
        shown = os.path.relpath(src, args.folder)
        # NFC 이름의 다른 파일이 이미 있으면 덮어쓰지 않습니다
        # (맥처럼 두 모양을 같은 이름으로 보는 디스크에서는 samefile 이 참이라 그대로 진행합니다)
        if os.path.exists(dst) and not os.path.samefile(src, dst):
            print(f"  건너뜀(같은 이름이 이미 있음): {show_name(shown)} → {new}")
            skipped += 1
            continue
        print(f"  {show_name(shown)}  →  {new}")
        if args.apply:
            os.rename(src, dst)
        done += 1
    if args.apply:
        print(f"완료: {done}개 변경, {skipped}개 건너뜀")
    else:
        print(f"미리보기: {done}개 바뀔 예정, {skipped}개 건너뜀. 실제로 바꾸려면 --apply 를 붙이세요.")


def show_name(name):
    """NFD 이름은 화면에서 멀쩡해 보일 수 있어, 글자 수를 같이 보여 줍니다."""
    return f"{name} (글자 {len(name)}개)"


if __name__ == "__main__":
    main()
