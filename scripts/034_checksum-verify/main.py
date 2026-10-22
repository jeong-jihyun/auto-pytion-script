"""파일 무결성 점검(체크섬) 스크립트.

폴더 안 모든 파일의 SHA-256 해시를 목록 파일(manifest)로 만들고(make),
나중에 같은 폴더를 목록과 비교해(verify) 바뀐 파일·없어진 파일·새로 생긴 파일을 알려 줍니다.
 - 전달받은 파일이 중간에 바뀌지 않았는지
 - 배치/이관 후 파일이 빠짐없이 옮겨졌는지
확인할 때 씁니다. 파일은 읽기만 하고 바꾸지 않습니다.
"""
import argparse
import hashlib
import sys
from pathlib import Path


def sha256(path):
    """큰 파일도 메모리를 아끼도록 조금씩 읽어서 해시를 만듭니다."""
    h = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def scan(folder):
    """{상대경로: 해시} 사전을 만듭니다."""
    return {str(f.relative_to(folder)).replace("\\", "/"): sha256(f)
            for f in sorted(folder.rglob("*")) if f.is_file()}


def read_manifest(path):
    res = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            digest, name = line.split("  ", 1)  # sha256sum 과 같은 모양
            res[name] = digest
    return res


def main():
    p = argparse.ArgumentParser(description="폴더 체크섬 만들기/검증")
    p.add_argument("mode", choices=["make", "verify"])
    p.add_argument("folder", type=Path)
    p.add_argument("-m", "--manifest", type=Path, default=Path("output/manifest.sha256"))
    a = p.parse_args()
    if not a.folder.is_dir():
        sys.exit(f"[오류] 폴더가 아닙니다: {a.folder}")

    now = scan(a.folder)
    if a.mode == "make":
        a.manifest.parent.mkdir(parents=True, exist_ok=True)
        a.manifest.write_text("".join(f"{d}  {n}\n" for n, d in now.items()), encoding="utf-8")
        print(f"파일 {len(now)}개의 해시를 저장했습니다 -> {a.manifest}")
        return

    old = read_manifest(a.manifest)
    changed = [n for n in now if n in old and now[n] != old[n]]
    missing = [n for n in old if n not in now]
    added = [n for n in now if n not in old]
    print(f"검사 {len(old)}개 기준: 바뀜 {len(changed)}, 없어짐 {len(missing)}, 새로 생김 {len(added)}")
    for tag, items in (("바뀜", changed), ("없어짐", missing), ("새로 생김", added)):
        for n in items:
            print(f"  [{tag}] {n}")
    if not (changed or missing or added):
        print("모두 같습니다. 이상 없음.")
    sys.exit(1 if (changed or missing) else 0)


if __name__ == "__main__":
    main()
