"""폴더 구조를 마크다운 트리(들여쓴 목록)로 만들어 문서에 붙일 수 있게 하는 스크립트.

생각의 흐름:
  1) 폴더를 이름순으로 훑으며 폴더 먼저, 파일 나중에 나열합니다.
  2) --depth 로 깊이를 제한하고, --exclude 에 적은 이름(예: .git, node_modules)은 건너뜁니다.
  3) --size 를 켜면 파일 크기를 같이 적습니다.
  4) 심볼릭 링크는 따라가지 않아 무한 반복을 막습니다. 읽기만 하고 아무것도 바꾸지 않습니다.
"""
import argparse
import os
from pathlib import Path


def human(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f}{unit}" if unit == "B" else f"{n:.1f}{unit}"
        n /= 1024


def walk(path, depth, max_depth, exclude, size, lines):
    try:
        entries = sorted(os.scandir(path), key=lambda e: (not e.is_dir(follow_symlinks=False), e.name.lower()))
    except PermissionError:
        lines.append("  " * depth + "- (읽을 권한 없음)")
        return
    for e in entries:
        if e.name in exclude:
            continue
        pad = "  " * depth
        if e.is_dir(follow_symlinks=False):
            lines.append(f"{pad}- **{e.name}/**")
            if max_depth is None or depth + 1 < max_depth:
                walk(e.path, depth + 1, max_depth, exclude, size, lines)
        else:
            extra = f" ({human(e.stat(follow_symlinks=False).st_size)})" if size else ""
            lines.append(f"{pad}- {e.name}{extra}")


def main():
    p = argparse.ArgumentParser(description="폴더 트리 마크다운")
    p.add_argument("--root", required=True, help="대상 폴더")
    p.add_argument("--depth", type=int, help="최대 깊이(생략하면 끝까지)")
    p.add_argument("--exclude", nargs="*", default=[".git", "node_modules", "__pycache__"])
    p.add_argument("--size", action="store_true", help="파일 크기 표시")
    p.add_argument("--out", default="output/폴더구조.md")
    a = p.parse_args()
    root = Path(a.root)
    if not root.is_dir():
        raise SystemExit("폴더가 아닙니다: " + a.root)
    lines = [f"# {root.resolve().name} 폴더 구조", ""]
    walk(root, 0, a.depth, set(a.exclude), a.size, lines)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"완료: {len(lines) - 2}개 항목 -> {out}")


if __name__ == "__main__":
    main()
