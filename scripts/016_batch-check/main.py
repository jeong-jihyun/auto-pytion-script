"""배치 실행 결과 점검 스크립트.

야간·일일 배치가 끝난 뒤 '실행 결과 CSV'를 읽어서 아침에 확인할 문제를 골라 줍니다.
점검 항목:
  1. 실패   : 상태가 SUCCESS 가 아닌 작업
  2. 누락   : 있어야 할 작업(예상 목록)이 결과에 없음
  3. 지연   : 종료 시각이 마감 시각(--deadline)보다 늦음
  4. 장시간 : 걸린 시간이 --max-minutes 보다 김
  5. 0건    : 처리 건수가 --min-rows 보다 적음
같은 작업이 여러 번 있으면 시작 시각이 가장 늦은 것(마지막 실행)만 봅니다.
문제가 있으면 종료 코드 1 로 끝나서, 다른 스크립트에서 연결하기 좋습니다.
"""
import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path

시각형식 = "%Y-%m-%d %H:%M:%S"


def 시각(글):
    return datetime.strptime(글.strip(), 시각형식) if 글 and 글.strip() else None


def main():
    p = argparse.ArgumentParser(description="배치 실행 결과 점검")
    p.add_argument("runs", help="실행 결과 CSV (열: 작업명,시작,종료,상태,처리건수)")
    p.add_argument("-o", "--output", default="output/batch_check.csv", help="점검 결과 CSV")
    p.add_argument("--expected", help="있어야 할 작업 목록 txt (한 줄에 하나, #은 주석)")
    p.add_argument("--deadline", default="06:00", help="종료 마감 시각 HH:MM (기본 06:00)")
    p.add_argument("--max-minutes", type=float, default=60, help="허용 최대 소요 분 (기본 60)")
    p.add_argument("--min-rows", type=int, default=1, help="최소 처리 건수 (기본 1)")
    a = p.parse_args()

    마감 = datetime.strptime(a.deadline, "%H:%M").time()
    마지막 = {}
    with open(a.runs, newline="", encoding="utf-8-sig") as fp:
        for 행 in csv.DictReader(fp):
            try:
                시작 = 시각(행["시작"])
            except ValueError:
                print(f"[건너뜀] 시각 형식이 이상한 행: {행}")
                continue
            이름 = 행["작업명"].strip()
            if 이름 not in 마지막 or (시작 and 시작 > (시각(마지막[이름]["시작"]) or datetime.min)):
                마지막[이름] = 행

    결과 = []  # (작업명, 판정, 사유)
    for 이름, 행 in sorted(마지막.items()):
        문제 = []
        시작, 종료 = 시각(행["시작"]), 시각(행["종료"])
        if 행["상태"].strip().upper() != "SUCCESS":
            문제.append(("실패", f"상태 {행['상태']}"))
        if 종료 is None:
            문제.append(("지연", "종료 시각이 비어 있음(아직 도는 중이거나 비정상 종료)"))
        else:
            if 종료.time() > 마감 and 종료.date() >= (시작 or 종료).date():
                문제.append(("지연", f"종료 {종료:%H:%M} > 마감 {a.deadline}"))
            if 시작 and (종료 - 시작).total_seconds() / 60 > a.max_minutes:
                분 = (종료 - 시작).total_seconds() / 60
                문제.append(("장시간", f"{분:.0f}분 걸림 (허용 {a.max_minutes:g}분)"))
        try:
            건수 = int(str(행["처리건수"]).replace(",", "").strip() or 0)
        except ValueError:
            건수 = 0
        if 건수 < a.min_rows:
            문제.append(("0건", f"처리건수 {건수}"))
        if 문제:
            for 판정, 사유 in 문제:
                결과.append((이름, 판정, 사유))
        else:
            결과.append((이름, "정상", ""))

    if a.expected:
        for 줄 in Path(a.expected).read_text(encoding="utf-8").splitlines():
            이름 = 줄.strip()
            if 이름 and not 이름.startswith("#") and 이름 not in 마지막:
                결과.append((이름, "누락", "실행 결과에 없음"))

    out = Path(a.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["작업명", "판정", "사유"])
        w.writerows(결과)

    문제건 = [r for r in 결과 if r[1] != "정상"]
    print(f"점검 작업 {len(마지막)}개 중 문제 {len({r[0] for r in 문제건})}개 -> {out}")
    for 이름, 판정, 사유 in 문제건:
        print(f"  [{판정}] {이름}: {사유}")
    return 1 if 문제건 else 0


if __name__ == "__main__":
    sys.exit(main())
