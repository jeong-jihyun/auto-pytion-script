"""송·수신 파일(헤더/데이터/트레일러 구조)의 '건수·금액 합계'가 트레일러에 적힌 값과 맞는지 검증하는 스크립트.

생각의 흐름:
  1) 은행·카드사·VAN·대외기관과 주고받는 일괄 파일은 보통 이렇게 생겼습니다.
       H|20261030|기관코드          ← 헤더(1줄)
       D|...|금액|...              ← 데이터(여러 줄)
       T|데이터건수|금액합계         ← 트레일러(1줄)
  2) 파일이 중간에 잘리거나 두 번 붙거나 일부만 전송되면 트레일러 값과 실제 데이터가 달라집니다.
     그래서 받자마자 '실제로 센 값 = 트레일러 값' 인지 확인하는 것이 대사의 첫 단계입니다.
  3) 구분자(--delim)와 열 위치(0부터 셈)를 옵션으로 받아 여러 기관 파일 형식에 맞춥니다.
  4) 추가로 헤더가 정확히 1개인지, 트레일러가 마지막 줄인지, 알 수 없는 레코드 구분이 있는지,
     금액이 숫자가 아닌 줄이 있는지도 함께 봅니다.
  5) 결과가 맞으면 종료코드 0, 틀리면 1 → 배치 스케줄러에서 후속 작업을 막는 데 쓸 수 있습니다.
"""
import argparse
import sys
from decimal import Decimal, InvalidOperation


def main():
    p = argparse.ArgumentParser(description="헤더/트레일러 건수·합계 검증")
    p.add_argument("files", nargs="+")
    p.add_argument("--delim", default="|", help="구분자(기본 |, 탭은 '\\t')")
    p.add_argument("--type-col", type=int, default=0, help="레코드 구분 열 위치")
    p.add_argument("--header", default="H")
    p.add_argument("--data", default="D")
    p.add_argument("--trailer", default="T")
    p.add_argument("--amount-col", type=int, default=3, help="데이터 줄의 금액 열 위치")
    p.add_argument("--t-count-col", type=int, default=1, help="트레일러의 건수 열 위치")
    p.add_argument("--t-sum-col", type=int, default=2, help="트레일러의 금액합계 열 위치")
    p.add_argument("--encoding", default="utf-8-sig", help="cp949 등")
    a = p.parse_args()
    delim = "\t" if a.delim in ("\\t", "tab") else a.delim

    all_ok = True
    for path in a.files:
        problems = []
        n_head = n_data = 0
        total = Decimal(0)
        trailer = None
        trailer_line = None
        with open(path, encoding=a.encoding) as f:
            lines = [ln.rstrip("\r\n") for ln in f if ln.strip()]
        for no, line in enumerate(lines, 1):
            cols = line.split(delim)
            kind = cols[a.type_col].strip() if len(cols) > a.type_col else ""
            if kind == a.header:
                n_head += 1
            elif kind == a.data:
                n_data += 1
                try:
                    total += Decimal(cols[a.amount_col].replace(",", "").strip())
                except (IndexError, InvalidOperation):
                    problems.append(f"{no}행 금액 읽기 실패: {line[:60]}")
            elif kind == a.trailer:
                if trailer is not None:
                    problems.append(f"{no}행 트레일러가 또 있음(파일이 두 번 붙었을 수 있음)")
                trailer, trailer_line = cols, no
            else:
                problems.append(f"{no}행 알 수 없는 구분 '{kind}'")
        if n_head != 1:
            problems.append(f"헤더 개수 {n_head}개(1개여야 함)")
        if trailer is None:
            problems.append("트레일러 없음(전송이 중간에 끊겼을 수 있음)")
        else:
            if trailer_line != len(lines):
                problems.append(f"트레일러가 마지막 줄이 아님({trailer_line}행)")
            try:
                t_cnt = int(trailer[a.t_count_col].replace(",", "").strip())
                t_sum = Decimal(trailer[a.t_sum_col].replace(",", "").strip())
                if t_cnt != n_data:
                    problems.append(f"건수 불일치: 트레일러 {t_cnt:,} / 실제 {n_data:,} (차이 {n_data - t_cnt:+,})")
                if t_sum != total:
                    problems.append(f"금액 불일치: 트레일러 {t_sum:,} / 실제 {total:,} (차이 {total - t_sum:+,})")
            except (IndexError, ValueError, InvalidOperation):
                problems.append("트레일러 값 읽기 실패(열 위치 옵션 확인)")
        ok = not problems
        all_ok &= ok
        print(f"[{'일치' if ok else '불일치'}] {path}  데이터 {n_data:,}건 / 합계 {total:,}")
        for pr in problems:
            print(f"    - {pr}")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
