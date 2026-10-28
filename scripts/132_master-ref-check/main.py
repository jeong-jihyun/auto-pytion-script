"""거래 데이터의 코드(거래처·품목·부서 등)가 마스터에 실제로 있는지, 쓰지 않는 코드인지 점검하는 스크립트.

생각의 흐름:
  1) ERP로 전표·주문을 올리기 전, '거래처코드가 마스터에 없음' 같은 오류로 업로드가 통째로 실패하는 일이 잦습니다.
  2) 그래서 미리 '어느 줄의 어느 코드가 문제인지'를 목록으로 뽑아 고칠 수 있게 합니다.
  3) 규칙은 JSON 하나에 적습니다. 열마다 어느 마스터 파일의 어느 열과 맞춰 볼지 정합니다.
       {"거래처코드": {"master": "vendor_master.csv", "key": "코드",
                      "status_col": "사용여부", "active": ["Y"],
                      "valid_from": "시작일", "valid_to": "종료일", "date_col": "거래일"}}
  4) 결과 종류
       없음      : 마스터에 그 코드가 아예 없음
       사용중지  : 마스터에는 있지만 사용여부가 active 값이 아님
       기간외    : 거래일이 마스터의 유효기간(시작일~종료일) 밖
       빈값      : 코드 칸이 비어 있음(--allow-blank 열은 제외)
  5) 코드 앞뒤 공백·대소문자 차이는 흔한 실수라, 비교 전에 공백을 지우고(--ignore-case 시 대문자로) 맞춥니다.
"""
import argparse
import csv
import json
from collections import Counter
from datetime import datetime
from pathlib import Path


def norm(v, ignore_case):
    v = (v or "").strip()
    return v.upper() if ignore_case else v


def to_date(s):
    s = (s or "").strip()
    return datetime.strptime(s, "%Y-%m-%d").date() if s else None


def load_master(path, rule, ignore_case):
    with path.open(newline="", encoding="utf-8-sig") as fp:
        rows = list(csv.DictReader(fp))
    m = {}
    for r in rows:
        m[norm(r.get(rule["key"]), ignore_case)] = r
    return m


def main():
    p = argparse.ArgumentParser(description="마스터 코드 참조 점검")
    p.add_argument("data", type=Path, help="점검할 거래 CSV")
    p.add_argument("--rules", type=Path, required=True, help="규칙 JSON (master 경로는 규칙 파일 기준 상대경로 가능)")
    p.add_argument("--allow-blank", default="", help="빈칸을 허용할 열, 쉼표로")
    p.add_argument("--ignore-case", action="store_true", help="대소문자를 구분하지 않음")
    p.add_argument("-o", "--output", type=Path, default=Path("output/ref_issues.csv"))
    a = p.parse_args()

    rules = json.loads(a.rules.read_text(encoding="utf-8"))
    allow_blank = {c.strip() for c in a.allow_blank.split(",") if c.strip()}
    masters = {}
    for col, rule in rules.items():
        mp = Path(rule["master"])
        if not mp.is_absolute():
            mp = a.rules.parent / mp
        masters[col] = load_master(mp, rule, a.ignore_case)

    with a.data.open(newline="", encoding="utf-8-sig") as fp:
        rows = list(csv.DictReader(fp))

    issues = []
    for line_no, r in enumerate(rows, start=2):  # 1행은 머리글
        for col, rule in rules.items():
            code = norm(r.get(col), a.ignore_case)
            if not code:
                if col not in allow_blank:
                    issues.append((line_no, col, "", "빈값", "코드가 비어 있음"))
                continue
            m = masters[col].get(code)
            if m is None:
                issues.append((line_no, col, code, "없음", "마스터에 없는 코드"))
                continue
            sc = rule.get("status_col")
            if sc and (m.get(sc) or "").strip() not in rule.get("active", ["Y"]):
                issues.append((line_no, col, code, "사용중지", f"{sc}={m.get(sc, '').strip()}"))
                continue
            dc = rule.get("date_col")
            if dc and (rule.get("valid_from") or rule.get("valid_to")):
                d = to_date(r.get(dc))
                f = to_date(m.get(rule.get("valid_from", ""), "")) if rule.get("valid_from") else None
                t = to_date(m.get(rule.get("valid_to", ""), "")) if rule.get("valid_to") else None
                if d and ((f and d < f) or (t and d > t)):
                    issues.append((line_no, col, code, "기간외", f"{dc}={d}, 유효 {f or ''}~{t or ''}"))

    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["행번호", "열", "코드", "문제", "설명"])
        w.writerows(issues)

    print(f"점검 {len(rows)}줄, 문제 {len(issues)}건, 문제 있는 줄 {len({i[0] for i in issues})}개")
    for (col, kind), n in sorted(Counter((i[1], i[3]) for i in issues).items()):
        print(f"  {col} / {kind}: {n}건")
    print(f"저장: {a.output}")


if __name__ == "__main__":
    main()
