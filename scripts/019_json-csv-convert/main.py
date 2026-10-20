"""JSON <-> CSV 변환 스크립트.

  to-csv  : JSON(객체 목록 [{...}, {...}])을 CSV로. 안쪽 객체는 'a.b' 같은 열 이름으로 펼칩니다.
  to-json : CSV를 JSON 목록으로. 열 이름에 'a.b' 가 있으면 다시 안쪽 객체로 묶습니다.
쓰임: API 응답 JSON을 엑셀로 보고 싶을 때, 엑셀 표를 JSON 설정/테스트 데이터로 바꾸고 싶을 때.
- 목록(리스트) 값은 CSV에서 JSON 글자 그대로 저장되고, to-json 때 다시 목록으로 복원됩니다.
- CSV의 빈 칸은 기본으로 '키 없음'이 됩니다(--keep-empty 로 "" 유지).
- --infer 를 쓰면 to-json 에서 숫자처럼 보이는 글자를 숫자로 바꿉니다.
"""
import argparse
import csv
import json
import sys
from pathlib import Path


def 펼치기(값, 앞이름=""):
    """{"a": {"b": 1}} -> {"a.b": 1}"""
    결과 = {}
    for 키, v in 값.items():
        이름 = f"{앞이름}.{키}" if 앞이름 else str(키)
        if isinstance(v, dict) and v:
            결과.update(펼치기(v, 이름))
        elif isinstance(v, (list, dict)):
            결과[이름] = json.dumps(v, ensure_ascii=False)
        else:
            결과[이름] = "" if v is None else v
    return 결과


def 숫자_추측(글):
    if not isinstance(글, str):
        return 글
    try:
        return int(글)
    except ValueError:
        pass
    try:
        return float(글)
    except ValueError:
        return 글


def 묶기(펼친, 추측, 빈칸유지):
    결과 = {}
    for 이름, v in 펼친.items():
        if v == "" and not 빈칸유지:
            continue  # 빈 칸은 '값 없음'으로 보고 키를 만들지 않습니다
        if isinstance(v, str) and v[:1] in "[{":
            try:
                v = json.loads(v)  # 펼칠 때 글자로 바꿔 둔 목록을 되돌림
            except ValueError:
                pass
        elif 추측:
            v = 숫자_추측(v)
        칸 = 결과
        *앞, 끝 = 이름.split(".")
        for 조각 in 앞:
            칸 = 칸.setdefault(조각, {})
        칸[끝] = v
    return 결과


def csv로(a):
    자료 = json.loads(Path(a.input).read_text(encoding="utf-8"))
    if isinstance(자료, dict):
        자료 = [자료]
    if not isinstance(자료, list) or not all(isinstance(x, dict) for x in 자료):
        print("[오류] JSON 은 객체 목록([{...}, ...]) 이어야 합니다.")
        return 1
    행들 = [펼치기(x) for x in 자료]
    열들 = []
    for r in 행들:  # 처음 나온 순서대로 열을 모읍니다(행마다 키가 달라도 OK)
        for k in r:
            if k not in 열들:
                열들.append(k)
    out = Path(a.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.DictWriter(fp, fieldnames=열들)
        w.writeheader()
        w.writerows(행들)
    print(f"완료: {len(행들)}행, {len(열들)}열 -> {out}")
    return 0


def json으로(a):
    with open(a.input, newline="", encoding="utf-8-sig") as fp:
        행들 = [묶기(r, a.infer, a.keep_empty) for r in csv.DictReader(fp)]
    out = Path(a.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(행들, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"완료: {len(행들)}개 객체 -> {out}")
    return 0


def main():
    p = argparse.ArgumentParser(description="JSON <-> CSV 변환")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("to-csv")
    c.add_argument("input")
    c.add_argument("-o", "--output", default="output/data.csv")
    c.set_defaults(func=csv로)
    j = sub.add_parser("to-json")
    j.add_argument("input")
    j.add_argument("-o", "--output", default="output/data.json")
    j.add_argument("--keep-empty", action="store_true", help="빈 칸도 \"\" 값으로 남김")
    j.add_argument("--infer", action="store_true", help="숫자처럼 보이는 글자를 숫자로 바꿈")
    j.set_defaults(func=json으로)
    a = p.parse_args()
    try:
        return a.func(a)
    except (ValueError, OSError) as e:
        print(f"[오류] {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
