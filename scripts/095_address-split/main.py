"""한 줄로 된 한국 주소를 시도 / 시군구 / 나머지로 나누는 스크립트.

생각의 흐름:
  1) 첫 단어가 시도 이름이면 떼어 냅니다. '서울', '경기' 같은 줄임말은 정식 이름으로 바꿉니다.
  2) 그다음 단어가 '시·군·구'로 끝나면 시군구로 떼어 냅니다.
     (수원시 영통구처럼 시 뒤에 구가 또 오면 함께 묶습니다.)
  3) 남은 부분은 '상세주소'입니다.
  4) 시도를 못 찾으면 '확인필요'로 표시해 사람이 보게 합니다.
"""
import argparse
import csv
from pathlib import Path

SIDO = {
    "서울": "서울특별시", "서울시": "서울특별시", "서울특별시": "서울특별시",
    "부산": "부산광역시", "부산시": "부산광역시", "부산광역시": "부산광역시",
    "대구": "대구광역시", "대구광역시": "대구광역시",
    "인천": "인천광역시", "인천광역시": "인천광역시",
    "광주": "광주광역시", "광주광역시": "광주광역시",
    "대전": "대전광역시", "대전광역시": "대전광역시",
    "울산": "울산광역시", "울산광역시": "울산광역시",
    "세종": "세종특별자치시", "세종특별자치시": "세종특별자치시",
    "경기": "경기도", "경기도": "경기도", "강원": "강원특별자치도", "강원도": "강원특별자치도",
    "강원특별자치도": "강원특별자치도", "충북": "충청북도", "충청북도": "충청북도",
    "충남": "충청남도", "충청남도": "충청남도", "전북": "전북특별자치도",
    "전라북도": "전북특별자치도", "전북특별자치도": "전북특별자치도",
    "전남": "전라남도", "전라남도": "전라남도", "경북": "경상북도", "경상북도": "경상북도",
    "경남": "경상남도", "경상남도": "경상남도", "제주": "제주특별자치도",
    "제주도": "제주특별자치도", "제주특별자치도": "제주특별자치도",
}


def split_address(addr):
    words = addr.split()
    if not words or words[0] not in SIDO:
        return "", "", addr.strip(), "확인필요"
    sido, rest = SIDO[words[0]], words[1:]
    gungu = ""
    if rest and rest[0][-1] in "시군구" and len(rest[0]) > 1:
        gungu = rest.pop(0)
        if rest and gungu.endswith("시") and rest[0].endswith("구"):
            gungu += " " + rest.pop(0)
    return sido, gungu, " ".join(rest), "" if gungu else "시군구 없음"


def main():
    p = argparse.ArgumentParser(description="주소 분리")
    p.add_argument("--input", required=True, help="CSV 파일")
    p.add_argument("--column", default="주소", help="주소가 있는 컬럼 이름")
    p.add_argument("--out", default="output/주소분리.csv")
    a = p.parse_args()

    with open(a.input, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fields = reader.fieldnames
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    bad = 0
    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields + ["시도", "시군구", "상세주소", "비고"])
        w.writeheader()
        for r in rows:
            s, g, d, note = split_address(r[a.column])
            bad += bool(note)
            w.writerow({**r, "시도": s, "시군구": g, "상세주소": d, "비고": note})
    print(f"완료: {len(rows)}건 (확인 필요 {bad}건) -> {out}")


if __name__ == "__main__":
    main()
