"""웹 주소(URL) 목록이 살아 있는지 한 번에 점검하는 스크립트.

생각의 흐름:
  1) 아침마다 사내 시스템·API 주소를 브라우저로 하나씩 열어 보는 일은 번거롭고 빠뜨리기 쉽습니다.
  2) 점검할 주소를 CSV(이름, url, 기대코드, 기준ms, 포함문구)로 적어 두고, 주소마다 한 번씩 요청을 보냅니다.
  3) 결과를 4가지로 나눕니다.
       정상 : 기대한 응답 코드 + 기준 시간 안 + (포함문구가 있으면) 본문에 그 글자가 있음
       느림 : 응답은 맞는데 기준 시간보다 오래 걸림
       이상 : 응답 코드가 다르거나 포함문구가 없음
       실패 : 연결 자체가 안 됨(타임아웃, 주소 없음 등)
  4) 결과를 화면과 CSV로 남기고, 정상이 아닌 것이 있으면 종료 코드 1을 돌려줍니다(배치·스케줄러가 알 수 있게).
  ※ 남의 사이트를 짧은 간격으로 반복 요청하지 마세요. 내가 관리하는 주소나 허락받은 주소만 점검합니다.
"""
import argparse
import csv
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path


def check(url, timeout, expect, limit_ms, contains):
    req = urllib.request.Request(url, headers={"User-Agent": "url-health-check/1.0 (internal monitoring)"})
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            code = res.status
            body = res.read(200_000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:  # 4xx, 5xx 도 '응답은 온 것'
        code, body = e.code, ""
    except Exception as e:  # 연결 실패
        ms = int((time.perf_counter() - start) * 1000)
        return "실패", "", ms, f"{type(e).__name__}: {e}"
    ms = int((time.perf_counter() - start) * 1000)
    if code != expect:
        return "이상", code, ms, f"기대 {expect}, 실제 {code}"
    if contains and contains not in body:
        return "이상", code, ms, f"본문에 '{contains}' 없음"
    if ms > limit_ms:
        return "느림", code, ms, f"기준 {limit_ms}ms 초과"
    return "정상", code, ms, ""


def main():
    p = argparse.ArgumentParser(description="URL 목록 상태 점검")
    p.add_argument("targets", type=Path, help="CSV(이름,url,기대코드,기준ms,포함문구) - 뒤 3개는 비워도 됨")
    p.add_argument("--timeout", type=float, default=5, help="주소당 최대 기다림(초, 기본 5)")
    p.add_argument("--default-ms", type=int, default=1000, help="기준ms가 비었을 때 기준(기본 1000)")
    p.add_argument("-o", "--outdir", type=Path, default=Path("output"))
    a = p.parse_args()

    rows = []
    with a.targets.open(newline="", encoding="utf-8-sig") as fp:
        for r in csv.DictReader(fp):
            name, url = r["이름"].strip(), r["url"].strip()
            if not url or url.startswith("#"):
                continue
            expect = int(r.get("기대코드") or 200)
            limit = int(r.get("기준ms") or a.default_ms)
            contains = (r.get("포함문구") or "").strip()
            status, code, ms, note = check(url, a.timeout, expect, limit, contains)
            rows.append([name, url, status, code, ms, note])
            print(f"[{status}] {name:<14} {code!s:>4} {ms:>6}ms  {note}")

    a.outdir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = a.outdir / f"health_{stamp}.csv"
    with out.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["이름", "url", "상태", "응답코드", "응답ms", "메모"])
        w.writerows(rows)
    bad = [r for r in rows if r[2] != "정상"]
    print(f"\n총 {len(rows)}개 중 정상 {len(rows) - len(bad)}개, 확인 필요 {len(bad)}개 -> {out}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
