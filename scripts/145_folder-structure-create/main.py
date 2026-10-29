"""목록(CSV 또는 들여쓰기 텍스트)대로 폴더 구조를 한 번에 만드는 스크립트.

생각의 흐름:
  1) 새 프로젝트·새 연도·새 분기가 시작되면 '부서/연도/월/문서종류' 같은 폴더를 손으로 수십 개 만듭니다.
     사람마다 이름이 조금씩 달라져 나중에 찾기도 어렵습니다.
  2) 두 가지 입력을 받습니다.
       - 들여쓰기 텍스트(.txt): 들여쓰기(공백 2칸 또는 탭) 깊이가 곧 폴더 깊이
       - CSV: 한 줄이 한 경로, 열이 깊이 (예: 부서,연도,문서종류). 빈 칸은 그 깊이에서 멈춤
  3) 이름에 {year}, {month} 같은 자리표시를 쓰면 --var year=2027 처럼 바꿔 넣습니다.
     {month:01-12} 처럼 쓰면 01~12 로 펼쳐 12개를 만듭니다.
  4) 윈도우에서 쓸 수 없는 글자(\\ / : * ? " < > |)나 '..'가 들어간 이름은 거부합니다(엉뚱한 곳에 만들지 않게).
  5) 기본은 미리보기입니다. --apply 를 줘야 실제로 만들고, 이미 있는 폴더는 그대로 둡니다(아무것도 지우지 않음).
"""
import argparse
import csv
import re
from pathlib import Path

BAD = re.compile(r'[\\/:*?"<>|]')
RANGE = re.compile(r"\{(\w+):(\d+)-(\d+)\}")


def expand(name, vars_):
    """{month:01-12} 는 여러 이름으로 펼치고, {year} 는 값으로 바꿉니다."""
    m = RANGE.search(name)
    if m:
        lo, hi = m.group(2), m.group(3)
        width = len(lo)
        out = []
        for i in range(int(lo), int(hi) + 1):
            out.extend(expand(name[:m.start()] + str(i).zfill(width) + name[m.end():], vars_))
        return out
    try:
        name = name.format(**vars_)
    except KeyError as e:
        raise SystemExit(f"[오류] 자리표시 {e} 값이 없습니다. --var {e.args[0]}=값 을 주세요")
    return [name]


def check(name):
    name = name.strip()
    if not name or name in (".", "..") or BAD.search(name):
        raise SystemExit(f"[오류] 폴더 이름으로 쓸 수 없습니다: '{name}'")
    return name


def read_tree(path):
    """들여쓰기 텍스트 → 경로 목록(각 경로는 이름 리스트)."""
    paths, stack = [], []
    for raw in Path(path).read_text(encoding="utf-8-sig").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        line = raw.replace("\t", "  ")
        depth = (len(line) - len(line.lstrip(" "))) // 2
        if depth > len(stack):
            raise SystemExit(f"[오류] 들여쓰기가 한 번에 두 단계 이상 깊어졌습니다: '{raw}'")
        stack = stack[:depth] + [line.strip()]
        paths.append(list(stack))
    return paths


def read_csv(path):
    paths = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        next(reader, None)  # 첫 줄은 머리글
        for row in reader:
            parts = []
            for cell in row:
                if not cell.strip():
                    break
                parts.append(cell.strip())
            if parts:
                paths.append(parts)
    return paths


def main():
    p = argparse.ArgumentParser(description="목록대로 폴더 구조 일괄 생성 (기본 미리보기)")
    p.add_argument("spec", help="구조 파일 (.txt 들여쓰기 또는 .csv)")
    p.add_argument("--root", required=True, help="폴더를 만들 기준 위치")
    p.add_argument("--var", action="append", default=[], help="자리표시 값 (예: --var year=2027)")
    p.add_argument("--apply", action="store_true", help="실제로 만듭니다 (없으면 미리보기)")
    a = p.parse_args()

    vars_ = {}
    for v in a.var:
        if "=" not in v:
            raise SystemExit(f"[오류] --var 형식은 이름=값 입니다: {v}")
        k, val = v.split("=", 1)
        vars_[k.strip()] = val.strip()

    raw = read_csv(a.spec) if a.spec.lower().endswith(".csv") else read_tree(a.spec)

    # 경로마다 각 단계 이름을 펼쳐서 모든 조합을 만듭니다.
    targets = set()
    for parts in raw:
        combos = [[]]
        for part in parts:
            combos = [c + [check(n)] for c in combos for n in expand(part, vars_)]
        for c in combos:
            for i in range(1, len(c) + 1):  # 중간 폴더도 목록에 넣어 개수를 정확히 셉니다
                targets.add(tuple(c[:i]))

    root = Path(a.root)
    new, exist = 0, 0
    for t in sorted(targets):
        d = root.joinpath(*t)
        if d.is_dir():
            exist += 1
            continue
        new += 1
        if a.apply:
            d.mkdir(parents=True, exist_ok=True)
        if new <= 30:
            print(("[생성] " if a.apply else "[예정] ") + str(d))
    if new > 30:
        print(f"... 외 {new - 30}개")
    mode = "생성 완료" if a.apply else "미리보기 (실제로 만들려면 --apply)"
    print(f"\n전체 {len(targets)}개 중 새로 {new}개, 이미 있음 {exist}개 — {mode}")


if __name__ == "__main__":
    main()
