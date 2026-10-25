"""배치 로그의 START/END 줄을 짝지어 작업별 소요시간과 끝나지 않은 작업을 찾는 스크립트.

야간 배치 로그에는 보통 '시각 ... START 작업명', '시각 ... END 작업명 (상태)' 줄이 남습니다.
생각의 흐름:
  1) 줄마다 정규식으로 시각·START/END·작업명·상태를 뽑습니다.
  2) START를 만나면 작업명별로 시작 시각을 기억해 둡니다.
  3) END를 만나면 기억해 둔 시작 시각과 빼서 소요시간을 구합니다.
  4) 마지막까지 END가 없는 작업은 '미종료', START 없는 END는 '시작 기록 없음'으로 표시합니다.
  5) --max-minutes 보다 오래 걸린 작업은 '지연'으로 표시합니다.
"""
import argparse
import csv
import re
from datetime import datetime
from pathlib import Path

DEFAULT_PATTERN = (
    r"^(?P<ts>\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}).*?\b(?P<kind>START|END)\b\s+"
    r"(?P<job>[\w.\-]+)(?:\s+\(?(?P<status>[A-Z]+)\)?)?"
)


def main():
    p = argparse.ArgumentParser(description="배치 작업 소요시간 계산")
    p.add_argument("logs", type=Path, nargs="+", help="로그 파일(여러 개 가능)")
    p.add_argument("--pattern", default=DEFAULT_PATTERN, help="ts, kind, job, status 이름을 가진 정규식")
    p.add_argument("--max-minutes", type=float, default=60, help="이보다 오래 걸리면 '지연'")
    p.add_argument("-o", "--output", type=Path, default=Path("output/job_durations.csv"))
    a = p.parse_args()

    rx = re.compile(a.pattern)
    running, results = {}, []
    for log in a.logs:
        with log.open(encoding="utf-8", errors="replace") as fp:
            for ln, line in enumerate(fp, start=1):
                m = rx.search(line)
                if not m:
                    continue
                ts = datetime.fromisoformat(m["ts"].replace(" ", "T"))
                job = m["job"]
                if m["kind"] == "START":
                    if job in running:  # 끝나기 전에 또 시작: 앞의 것은 미종료로 남김
                        results.append(row(job, running[job], None, "", "미종료(재시작됨)", a.max_minutes))
                    running[job] = ts
                else:
                    start = running.pop(job, None)
                    status = m["status"] or ""
                    if start is None:
                        results.append(row(job, None, ts, status, "시작 기록 없음", a.max_minutes))
                    else:
                        results.append(row(job, start, ts, status, "", a.max_minutes))
    for job, start in running.items():
        results.append(row(job, start, None, "", "미종료", a.max_minutes))

    results.sort(key=lambda r: r["시작"] or r["종료"])
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.DictWriter(fp, fieldnames=["작업", "시작", "종료", "소요(분)", "상태", "판정"])
        w.writeheader()
        w.writerows(results)
    bad = [r for r in results if r["판정"] != "정상"]
    print(f"작업 {len(results)}건, 확인 필요 {len(bad)}건 → {a.output}")
    for r in bad:
        print(f"  - {r['작업']}: {r['판정']} {r['소요(분)'] and '(' + r['소요(분)'] + '분)'}")


def row(job, start, end, status, note, max_min):
    minutes = round((end - start).total_seconds() / 60, 1) if start and end else None
    if note:
        verdict = note
    elif status and status not in ("OK", "SUCCESS"):
        verdict = f"실패({status})"
    elif minutes is not None and minutes > max_min:
        verdict = "지연"
    else:
        verdict = "정상"
    return {
        "작업": job,
        "시작": start.isoformat(sep=" ") if start else "",
        "종료": end.isoformat(sep=" ") if end else "",
        "소요(분)": "" if minutes is None else str(minutes),
        "상태": status,
        "판정": verdict,
    }


if __name__ == "__main__":
    main()
