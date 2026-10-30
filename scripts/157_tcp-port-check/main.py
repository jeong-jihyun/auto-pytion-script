"""서버 목록 CSV(호스트, 포트)에 TCP 접속을 시도해 '열림/닫힘/시간초과'와 응답 시간을 점검하는 스크립트.

생각의 흐름:
  1) 아침 점검이나 작업 전후에 "DB 1521 열려 있나, MQ 1414 살아 있나, 대외 회선 포트 붙나"를
     하나씩 telnet 으로 확인하는 일을 목록 한 번 실행으로 끝냅니다.
  2) 방법은 단순합니다. socket.create_connection 으로 접속만 해 보고 바로 끊습니다.
     데이터를 보내지 않으므로 상대 서비스에 영향이 거의 없습니다.
  3) 결과는 세 가지로 나눕니다.
       - 열림: 접속 성공 (응답 시간 ms 기록)
       - 닫힘: 상대가 거부(ConnectionRefused) → 서비스가 내려갔을 가능성
       - 시간초과/오류: 방화벽·네트워크·DNS 문제 가능성
  4) '기대' 열에 open/closed 를 적어 두면 기대와 다를 때만 [이상] 으로 표시합니다
     (예: 작업 중 막혀 있어야 하는 포트가 열려 있으면 이상).
  5) 동시에 여러 개를 확인하도록 스레드를 씁니다(--workers). 이상이 하나라도 있으면 종료코드 1.
  ※ 내가 관리하거나 점검 허락을 받은 서버에만 쓰세요. 남의 서버 포트를 훑는 용도가 아닙니다.
"""
import argparse
import csv
import socket
import sys
import time
from concurrent.futures import ThreadPoolExecutor


def check(host, port, timeout):
    t0 = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return "open", round((time.perf_counter() - t0) * 1000, 1), ""
    except ConnectionRefusedError:
        return "closed", "", "접속 거부"
    except socket.timeout:
        return "timeout", "", f"{timeout}초 초과"
    except OSError as e:
        return "error", "", str(e)[:80]


def main():
    p = argparse.ArgumentParser(description="TCP 포트 점검")
    p.add_argument("targets_csv", help="CSV: 이름,호스트,포트[,기대(open/closed)]")
    p.add_argument("--timeout", type=float, default=3.0)
    p.add_argument("--workers", type=int, default=10)
    p.add_argument("-o", "--output", default="port_check.out.csv")
    a = p.parse_args()

    targets = list(csv.DictReader(open(a.targets_csv, encoding="utf-8-sig")))
    if len(targets) > 500:
        raise SystemExit("[중단] 대상이 500개를 넘습니다. 점검 목록을 나눠 주세요.")

    def run(t):
        status, ms, msg = check(t["호스트"].strip(), int(t["포트"]), a.timeout)
        expect = (t.get("기대") or "open").strip().lower()
        ok = (status == "open") == (expect == "open")
        return {"이름": t["이름"], "호스트": t["호스트"], "포트": t["포트"], "기대": expect,
                "결과": status, "응답ms": ms, "판정": "정상" if ok else "이상", "메시지": msg}

    with ThreadPoolExecutor(max_workers=max(1, a.workers)) as ex:
        rows = list(ex.map(run, targets))
    with open(a.output, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["이름"])
        w.writeheader()
        w.writerows(rows)
    bad = [r for r in rows if r["판정"] == "이상"]
    print(f"점검 {len(rows)}개 / 이상 {len(bad)}개 ({time.strftime('%Y-%m-%d %H:%M:%S')}) → {a.output}")
    for r in rows:
        mark = "[이상]" if r["판정"] == "이상" else "      "
        extra = f"{r['응답ms']}ms" if r["응답ms"] != "" else r["메시지"]
        print(f"  {mark} {r['이름']:<12} {r['호스트']}:{r['포트']}  {r['결과']} (기대 {r['기대']}) {extra}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
