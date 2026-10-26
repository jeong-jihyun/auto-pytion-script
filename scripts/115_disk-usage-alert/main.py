"""여러 경로(드라이브·마운트)의 디스크 사용률을 기준치와 비교해 경고 목록을 만드는 스크립트.

생각의 흐름:
  1) 야간 배치가 '디스크 가득 참'으로 실패하는 일이 흔합니다. 미리 사용률을 보면 막을 수 있습니다.
  2) 점검할 경로와 경고/위험 기준(%)을 CSV에 적어 둡니다. 경로마다 기준을 다르게 줄 수 있습니다.
  3) 파이썬 표준 기능 shutil.disk_usage 로 전체·사용·남은 용량을 읽고 사용률을 계산합니다.
  4) 상태를 정상/경고/위험/경로없음 으로 나누고 CSV로 저장합니다.
  5) 위험이 하나라도 있으면 종료 코드 2, 경고만 있으면 1을 돌려줘서
     작업 스케줄러가 실패로 알아차리게 합니다.
"""
import argparse
import csv
import shutil
import sys
from datetime import datetime
from pathlib import Path

GB = 1024 ** 3


def main():
    p = argparse.ArgumentParser(description="디스크 사용률 경고")
    p.add_argument("targets", type=Path, help="CSV(이름,경로,경고퍼센트,위험퍼센트)")
    p.add_argument("-o", "--output", type=Path, default=Path("output/disk_usage.csv"))
    a = p.parse_args()

    rows, worst = [], 0
    with a.targets.open(newline="", encoding="utf-8-sig") as fp:
        for r in csv.DictReader(fp):
            path = Path(r["경로"].strip()).expanduser()
            warn, crit = float(r.get("경고퍼센트") or 80), float(r.get("위험퍼센트") or 90)
            if not path.exists():
                rows.append([r["이름"], str(path), "", "", "", "", "경로없음"])
                worst = max(worst, 1)
                continue
            u = shutil.disk_usage(path)
            # df 명령과 같은 방식: 사용 ÷ (사용 + 일반 사용자가 쓸 수 있는 남은 공간)
            pct = u.used / (u.used + u.free) * 100 if (u.used + u.free) else 0
            state, level = ("위험", 2) if pct >= crit else ("경고", 1) if pct >= warn else ("정상", 0)
            worst = max(worst, level)
            rows.append([r["이름"], str(path), round(u.total / GB, 1), round(u.used / GB, 1),
                         round(u.free / GB, 1), round(pct, 1), state])

    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["이름", "경로", "전체GB", "사용GB", "남은GB", "사용률%", "상태"])
        w.writerows(rows)
    print(f"[{datetime.now():%Y-%m-%d %H:%M}] {len(rows)}개 경로 점검 → {a.output}")
    for r in rows:
        if r[6] == "경로없음":
            print(f"  경로없음 {r[0]} ({r[1]})")
        else:
            print(f"  {r[6]:4} {r[0]} ({r[1]}) 사용률 {r[5]}% 남은 {r[4]}GB")
    sys.exit(worst)


if __name__ == "__main__":
    main()
