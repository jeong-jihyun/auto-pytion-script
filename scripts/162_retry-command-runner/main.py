"""배치 명령을 실행하다 실패하면 정해진 횟수만큼 기다렸다가 다시 실행하고, 시도마다 결과를 기록하는 스크립트.

생각의 흐름:
  1) 파일 전송·외부 연동 배치는 네트워크가 잠깐 끊겨 실패했다가 다시 돌리면 되는 일이 많습니다.
     새벽에 사람이 손으로 재실행하지 않도록 '재시도 감싸개(wrapper)'를 만듭니다.
  2) 안전을 위해 셸(shell=True)을 쓰지 않고, 명령을 목록으로 받아 그대로 실행합니다.
     (사용법: python main.py [옵션] -- 실행할 명령 인자...)
  3) 재시도 간격은 처음엔 짧게, 점점 길게(지수 백오프) 늘릴 수 있게 했습니다.
       기다림 = delay × backoff^(시도-1), 최대 --max-delay
  4) 어떤 종료 코드는 '다시 해도 소용없는 실패'(예: 입력 파일 형식 오류)일 수 있어
     --no-retry-codes 로 지정하면 바로 멈춥니다.
  5) 너무 오래 걸리는 실행은 --timeout 으로 끊고 실패로 봅니다.
  6) 시도별 시작 시각·소요 시간·종료 코드·출력 마지막 줄을 CSV로 남겨 아침 점검 때 보게 합니다.
  7) 이 스크립트의 종료 코드는 마지막 시도의 종료 코드와 같게 해서, 상위 스케줄러가 성공/실패를 알 수 있게 했습니다.
"""
import argparse
import csv
import os
import subprocess
import sys
import time
from datetime import datetime


def last_line(text):
    lines = [x for x in (text or "").strip().splitlines() if x.strip()]
    return lines[-1][:200] if lines else ""


def main():
    p = argparse.ArgumentParser(
        description="실패하면 다시 실행하는 배치 명령 실행기",
        usage="python main.py [옵션] -- 명령 [인자 ...]")
    p.add_argument("--retries", type=int, default=3, help="실패 후 다시 시도할 횟수(기본 3 → 최대 4번 실행)")
    p.add_argument("--delay", type=float, default=5, help="첫 재시도 전 기다릴 초(기본 5)")
    p.add_argument("--backoff", type=float, default=2, help="재시도마다 기다림을 몇 배로 늘릴지(기본 2)")
    p.add_argument("--max-delay", type=float, default=300, help="기다림 최대 초(기본 300)")
    p.add_argument("--timeout", type=float, default=None, help="한 번 실행 제한 시간(초). 넘으면 실패로 봄")
    p.add_argument("--no-retry-codes", default="", help="재시도하지 않을 종료 코드(쉼표). 예: 2,64")
    p.add_argument("--log", default="retry_log.out.csv", help="시도 기록 CSV(이어 쓰기)")
    p.add_argument("--name", default="", help="기록에 남길 작업 이름(기본: 명령 첫 단어)")
    p.add_argument("command", nargs=argparse.REMAINDER, help="-- 뒤에 실행할 명령")
    a = p.parse_args()

    cmd = a.command[1:] if a.command and a.command[0] == "--" else a.command
    if not cmd:
        p.error("실행할 명령이 없습니다. 예: python main.py --retries 2 -- python job.py")
    no_retry = {int(x) for x in a.no_retry_codes.split(",") if x.strip()}
    name = a.name or os.path.basename(cmd[0])

    new_file = not os.path.exists(a.log)
    logf = open(a.log, "a", newline="", encoding="utf-8-sig")
    w = csv.writer(logf)
    if new_file:
        w.writerow(["작업", "시도", "시작", "소요초", "종료코드", "결과", "출력 마지막 줄"])

    code = 1
    total = a.retries + 1
    for attempt in range(1, total + 1):
        start = datetime.now()
        t0 = time.monotonic()
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=a.timeout)
            code, out = r.returncode, (r.stdout or "") + (r.stderr or "")
            result = "성공" if code == 0 else "실패"
        except subprocess.TimeoutExpired as e:
            code, result = 124, "시간초과"
            out = (e.stdout or b"").decode(errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
        except FileNotFoundError:
            code, result, out = 127, "명령 없음", f"명령을 찾을 수 없습니다: {cmd[0]}"
        took = time.monotonic() - t0
        w.writerow([name, attempt, start.strftime("%Y-%m-%d %H:%M:%S"), f"{took:.2f}", code, result, last_line(out)])
        logf.flush()
        print(f"[{attempt}/{total}] {result} (종료코드 {code}, {took:.2f}초) {last_line(out)}")

        if code == 0:
            break
        if code in no_retry or result == "명령 없음":
            print("  → 다시 해도 소용없는 실패로 보고 멈춥니다.")
            break
        if attempt < total:
            wait = min(a.delay * (a.backoff ** (attempt - 1)), a.max_delay)
            print(f"  → {wait:g}초 기다렸다가 다시 시도합니다.")
            time.sleep(wait)

    logf.close()
    print(f"최종: {'성공' if code == 0 else '실패'} (종료코드 {code}), 기록 → {a.log}")
    sys.exit(code)


if __name__ == "__main__":
    main()
