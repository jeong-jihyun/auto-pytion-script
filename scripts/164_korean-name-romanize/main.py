"""한글 이름을 로마자(영문)로 바꾸는 스크립트. 국어의 로마자 표기법(인명 규칙)과 흔히 쓰는 성씨 표기를 함께 보여 줍니다.

생각의 흐름:
  1) 해외 출장 명단, 영문 명함, 영문 증명서를 만들 때 사람마다 영문 이름을 손으로 적다 보면 틀리기 쉽습니다.
  2) 한글 한 글자는 유니코드에서 '초성·중성·종성' 번호로 계산해 나눌 수 있습니다.
       글자코드 - 0xAC00 = (초성×21 + 중성)×28 + 종성
     나눈 뒤 각 자모를 표기법 표대로 바꾸면 됩니다.
  3) 인명은 소리 나는 대로 바꾸지 않고(예: 복남 → Boknam, 'Bongnam' 아님) 글자별로 적는 것이 규칙입니다.
     단, 앞 글자 받침 ㄹ + 뒤 글자 첫소리 ㄹ 은 'll' 로 적습니다.
  4) 성씨는 표준 표기(김 Gim, 이 I, 박 Bak)와 실제 많이 쓰는 표기(Kim, Lee, Park)가 달라서
     두 가지를 모두 보여 주고, --surname 으로 어느 쪽을 '최종'에 쓸지 고릅니다.
  5) 두 글자 성(남궁, 황보, 제갈 등)은 목록으로 먼저 확인합니다.
  6) CSV에 이미 '영문' 열이 있으면 계산 결과와 비교해 '다름' 표시를 해서 명부 검수에 쓰게 했습니다.
     (여권 영문 이름은 본인이 정한 것이 우선이므로 '다름'은 틀렸다는 뜻이 아니라 확인하라는 뜻입니다.)
"""
import argparse
import csv
import re
import sys

CHO = ["g", "kk", "n", "d", "tt", "r", "m", "b", "pp", "s", "ss", "", "j", "jj", "ch", "k", "t", "p", "h"]
JUNG = ["a", "ae", "ya", "yae", "eo", "e", "yeo", "ye", "o", "wa", "wae", "oe", "yo", "u", "wo", "we", "wi",
        "yu", "eu", "ui", "i"]
JONG = ["", "k", "k", "k", "n", "n", "n", "t", "l", "k", "m", "l", "l", "l", "p", "l", "m", "p", "p", "t", "t",
        "ng", "t", "t", "k", "t", "p", "t"]

TWO_CHAR_SURNAMES = {"남궁", "황보", "제갈", "선우", "독고", "사공", "서문", "동방", "을지", "망절"}

# 흔히 쓰는 성씨 영문 표기(관용). 없는 성은 표준 표기를 그대로 씁니다.
COMMON = {
    "김": "Kim", "이": "Lee", "박": "Park", "최": "Choi", "정": "Jung", "강": "Kang", "조": "Cho", "윤": "Yoon",
    "장": "Jang", "임": "Lim", "한": "Han", "오": "Oh", "서": "Seo", "신": "Shin", "권": "Kwon", "황": "Hwang",
    "안": "Ahn", "송": "Song", "류": "Ryu", "유": "Yoo", "홍": "Hong", "전": "Jeon", "고": "Ko", "문": "Moon",
    "양": "Yang", "손": "Son", "배": "Bae", "백": "Baek", "허": "Heo", "노": "Noh", "남": "Nam", "심": "Shim",
    "하": "Ha", "곽": "Kwak", "성": "Sung", "차": "Cha", "주": "Joo", "우": "Woo", "구": "Koo", "나": "Na",
    "민": "Min", "진": "Jin", "지": "Ji", "엄": "Eom", "변": "Byun", "채": "Chae", "원": "Won", "방": "Bang",
    "천": "Cheon", "공": "Kong", "현": "Hyun", "함": "Ham", "염": "Yeom", "여": "Yeo", "추": "Choo", "도": "Do",
    "소": "So", "석": "Seok", "선": "Sun", "설": "Seol", "마": "Ma", "길": "Gil", "연": "Yeon", "표": "Pyo",
    "명": "Myung", "기": "Ki", "반": "Ban", "왕": "Wang", "금": "Keum", "옥": "Ok", "육": "Yook", "인": "In",
    "맹": "Maeng", "제": "Je", "모": "Mo", "탁": "Tak", "국": "Kook", "은": "Eun", "편": "Pyun", "경": "Kyung",
    "봉": "Bong", "태": "Tae", "형": "Hyung", "두": "Doo", "감": "Kam", "범": "Bum", "승": "Seung",
    "남궁": "Namgoong", "황보": "Hwangbo", "제갈": "Jegal", "선우": "Sunwoo", "독고": "Dokgo", "사공": "Sagong",
    "서문": "Seomun",
}


def split_jamo(ch):
    code = ord(ch) - 0xAC00
    if not 0 <= code < 11172:
        return None
    return code // 588, (code % 588) // 28, code % 28


def romanize(word):
    """한글 글자를 글자별로 로마자로. 받침 ㄹ + 첫소리 ㄹ 은 ll."""
    parts = []
    prev_jong = None
    for ch in word:
        j = split_jamo(ch)
        if j is None:
            raise ValueError(f"한글이 아닌 글자가 있습니다: '{ch}'")
        cho, jung, jong = j
        c = CHO[cho]
        if cho == 5 and prev_jong == 8:  # 앞 받침 ㄹ(8) + 이번 초성 ㄹ(5)
            c = "l"
        parts.append(c + JUNG[jung] + JONG[jong])
        prev_jong = jong
    return parts


def split_name(name):
    name = re.sub(r"\s+", "", name)
    if len(name) >= 3 and name[:2] in TWO_CHAR_SURNAMES:
        return name[:2], name[2:]
    return name[:1], name[1:]


def convert(name, a):
    sur, given = split_name(name)
    sur_std = "".join(romanize(sur)).capitalize()
    sur_common = COMMON.get(sur, sur_std)
    g = romanize(given)
    given_join = "".join(g).capitalize()
    given_hyphen = "-".join(g).capitalize()
    sur_final = sur_common if a.surname == "common" else sur_std
    given_final = given_hyphen if a.hyphen else given_join
    if a.style == "passport":
        final = f"{sur_final.upper()} {given_final.upper()}"
    elif a.style == "western":
        final = f"{given_final} {sur_final}"
    else:
        final = f"{sur_final} {given_final}"
    return {"성(한글)": sur, "이름(한글)": given, "성_표준": sur_std, "성_관용": sur_common,
            "이름_붙임": given_join, "이름_하이픈": given_hyphen, "최종": final}


def norm(s):
    return re.sub(r"[\s\-]", "", s or "").lower()


def main():
    p = argparse.ArgumentParser(description="한글 이름 → 로마자 변환")
    p.add_argument("names", nargs="*", help="바로 바꿀 이름들(예: 홍길동 남궁민수)")
    p.add_argument("--csv", help="이름 열이 있는 CSV(영문 열이 있으면 비교)")
    p.add_argument("--column", default="이름", help="CSV의 이름 열(기본 '이름')")
    p.add_argument("--english-column", default="영문", help="비교할 기존 영문 열(기본 '영문')")
    p.add_argument("-o", "--output", default="romanized.out.csv")
    p.add_argument("--surname", choices=["common", "standard"], default="common",
                   help="최종 표기에 쓸 성씨: common(Kim, Lee) / standard(Gim, I)")
    p.add_argument("--hyphen", action="store_true", help="이름 글자 사이에 하이픈(Gil-dong)")
    p.add_argument("--style", choices=["korean", "passport", "western"], default="korean",
                   help="korean: Hong Gildong / passport: HONG GILDONG / western: Gildong Hong")
    p.add_argument("--encoding", default="utf-8-sig")
    a = p.parse_args()

    if not a.names and not a.csv:
        p.error("이름을 적거나 --csv 를 주세요")

    for n in a.names:
        try:
            r = convert(n, a)
            print(f"{n} → {r['최종']}  (표준 성: {r['성_표준']}, 하이픈: {r['이름_하이픈']})")
        except ValueError as e:
            print(f"{n} → 변환 못 함: {e}", file=sys.stderr)

    if a.csv:
        with open(a.csv, newline="", encoding=a.encoding) as f:
            rows = list(csv.DictReader(f))
        out, diff = [], 0
        for row in rows:
            name = row.get(a.column, "").strip()
            try:
                r = convert(name, a)
            except ValueError as e:
                r = {"최종": "", "비고": str(e)}
            res = dict(row)
            res.update(r)
            if a.english_column in row and not row[a.english_column].strip():
                res["비교"] = "영문 없음"
            elif a.english_column in row and not r.get("최종"):
                res["비교"] = "-"
            elif a.english_column in row:
                given_ok = {norm(r.get("이름_붙임", ""))}
                sur_ok = {norm(r.get("성_표준", "")), norm(r.get("성_관용", ""))}
                old = norm(row[a.english_column])
                same = any(old in (s + g, g + s) for s in sur_ok for g in given_ok)
                res["비교"] = "같음" if same else "다름(확인)"
                diff += 0 if same else 1
            out.append(res)
        keys = []
        for r in out:
            for k in r:
                if k not in keys:
                    keys.append(k)
        with open(a.output, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=keys)
            w.writeheader()
            w.writerows(out)
        print(f"CSV {len(out)}명 변환 → {a.output}" + (f", 기존 영문과 다른 사람 {diff}명" if diff else ""))


if __name__ == "__main__":
    main()
