"""정해진 틀이 있는 텍스트(알림 문자, 시스템 메일 본문, 로그 등)에서 정규식으로 값을 뽑아 CSV로 만드는 스크립트.

생각의 흐름:
  1) 업무에서 받는 '입금 알림', '주문 접수 메일', '배치 완료 통보' 같은 글은 모양이 늘 같습니다.
     사람이 하나씩 엑셀에 옮겨 적는 대신, 규칙만 정해 두면 자동으로 표가 됩니다.
  2) 규칙은 JSON 파일에 적습니다. 정규식의 '이름 붙은 그룹' (?P<이름>...) 이 곧 CSV 열이 됩니다.
       {"name": "입금", "pattern": "\\[입금\\] (?P<날짜>\\d{2}/\\d{2}) (?P<금액>[\\d,]+)원 (?P<보낸분>\\S+)"}
     규칙을 여러 개 두면 첫 번째로 맞는 규칙을 씁니다(종류가 섞인 글도 처리).
  3) 입력 단위는 두 가지입니다.
       - 줄 단위(기본): 한 줄 = 한 건
       - 블록 단위(--block-sep): 빈 줄이나 구분선으로 나뉜 여러 줄 덩어리 = 한 건 (메일 본문 등)
  4) 어떤 규칙에도 맞지 않은 줄/블록은 따로 파일에 모아 규칙을 보완할 수 있게 합니다.
  5) --clean-number 열 이름을 주면 '1,234,000원' 같은 값에서 숫자만 남깁니다.
"""
import argparse
import csv
import json
import re
from pathlib import Path


def load_rules(path):
    rules = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    out = []
    for r in rules:
        try:
            rx = re.compile(r["pattern"], re.S)
        except re.error as e:
            raise SystemExit(f"[오류] 규칙 '{r.get('name')}' 정규식이 틀렸습니다: {e}")
        if not rx.groupindex:
            raise SystemExit(f"[오류] 규칙 '{r.get('name')}' 에 (?P<이름>...) 그룹이 없습니다")
        out.append((r.get("name", f"rule{len(out)+1}"), rx))
    return out


def read_units(files, block_sep):
    for f in files:
        text = Path(f).read_text(encoding="utf-8-sig")
        if block_sep is None:
            for i, line in enumerate(text.splitlines(), 1):
                if line.strip():
                    yield f"{Path(f).name}:{i}", line.strip()
        else:
            sep = r"\n\s*\n" if block_sep == "" else r"\n" + re.escape(block_sep) + r"\n"
            for i, block in enumerate(re.split(sep, text), 1):
                if block.strip():
                    yield f"{Path(f).name}#{i}", block.strip()


def main():
    p = argparse.ArgumentParser(description="정규식 규칙으로 텍스트에서 값 추출 → CSV")
    p.add_argument("rules", help="규칙 JSON 파일")
    p.add_argument("inputs", nargs="+", help="텍스트 파일(여러 개 가능)")
    p.add_argument("-o", "--output", default="extracted.out.csv")
    p.add_argument("--unmatched", default="unmatched.out.txt", help="어떤 규칙에도 안 맞은 내용")
    p.add_argument("--block-sep", nargs="?", const="", default=None,
                   help="블록 단위로 읽기. 값 없이 쓰면 빈 줄로 구분, 값을 주면 그 줄로 구분 (예: --block-sep=----, 반드시 = 로 붙여 쓰기)")
    p.add_argument("--clean-number", default="", help="숫자만 남길 열 이름(쉼표로 여러 개)")
    a = p.parse_args()

    rules = load_rules(a.rules)
    num_cols = {c.strip() for c in a.clean_number.split(",") if c.strip()}

    # 모든 규칙의 그룹 이름을 합쳐 열 목록을 만듭니다(나온 순서 유지).
    cols = []
    for _, rx in rules:
        for g in rx.groupindex:
            if g not in cols:
                cols.append(g)

    rows, unmatched, per_rule = [], [], {name: 0 for name, _ in rules}
    for where, unit in read_units(a.inputs, a.block_sep):
        for name, rx in rules:
            m = rx.search(unit)
            if m:
                rec = {"출처": where, "규칙": name}
                for k, v in m.groupdict().items():
                    v = (v or "").strip()
                    if k in num_cols:
                        v = re.sub(r"[^\d.\-]", "", v)
                    rec[k] = v
                rows.append(rec)
                per_rule[name] += 1
                break
        else:
            unmatched.append(f"[{where}]\n{unit}\n")

    with open(a.output, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["출처", "규칙"] + cols)
        w.writeheader()
        w.writerows(rows)
    if unmatched:
        Path(a.unmatched).write_text("\n".join(unmatched), encoding="utf-8")

    total = len(rows) + len(unmatched)
    print(f"전체 {total}건 중 추출 {len(rows)}건 → {a.output}")
    for name, n in per_rule.items():
        print(f"  규칙 '{name}': {n}건")
    if unmatched:
        print(f"  안 맞음 {len(unmatched)}건 → {a.unmatched} (규칙을 보완하세요)")


if __name__ == "__main__":
    main()
