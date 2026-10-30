"""배치 작업이 남긴 lock / pid 파일 중 '오래되었거나 주인이 없는' 파일을 찾아 점검표를 만드는 스크립트.

생각의 흐름:
  1) 배치는 중복 실행을 막으려고 시작할 때 xxx.lock, xxx.pid 파일을 만들고 끝날 때 지웁니다.
     그런데 배치가 비정상 종료되면 lock 파일이 남아 다음 날 배치가 "이미 실행 중"이라며 돌지 않습니다.
  2) 그래서 아침 점검 때 lock 폴더를 훑어 다음 두 가지를 찾습니다.
       - 오래된 파일: 수정 시각이 --max-age-min 분보다 오래됨
       - 주인 없는 pid: 파일 안 숫자(PID)의 프로세스가 지금 이 서버에 없음
         (리눅스는 /proc/<pid> 존재 여부, 그 밖의 OS는 os.kill(pid, 0) 으로 확인)
  3) 이 스크립트는 기본으로 '보고만' 합니다. --apply 를 주면 '삭제'가 아니라
     격리 폴더(--quarantine)로 옮겨, 혹시 잘못 판단해도 되돌릴 수 있게 합니다.
"""
import argparse
import csv
import os
import shutil
import time
from pathlib import Path


def pid_alive(pid):
    """PID 프로세스가 살아 있는지 확인합니다. 확인할 수 없으면 None."""
    if Path("/proc").is_dir():
        return Path(f"/proc/{pid}").exists()
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True   # 남의 프로세스지만 존재는 함
    except OSError:
        return None


def read_pid(path):
    try:
        text = path.read_text(encoding="utf-8", errors="ignore").strip().split()
        return int(text[0]) if text and text[0].isdigit() else None
    except OSError:
        return None


def main():
    p = argparse.ArgumentParser(description="오래된/주인 없는 lock·pid 파일 점검")
    p.add_argument("folder", help="lock 파일이 있는 폴더")
    p.add_argument("--patterns", default="*.lock,*.pid", help="찾을 파일 패턴(쉼표 구분)")
    p.add_argument("--max-age-min", type=float, default=180, help="이 분보다 오래되면 '오래됨'(기본 180)")
    p.add_argument("--quarantine", default="lock_quarantine_out", help="--apply 때 옮길 폴더")
    p.add_argument("--apply", action="store_true", help="문제 파일을 격리 폴더로 옮깁니다(기본은 보고만)")
    p.add_argument("-o", "--output", default="lock_check.out.csv")
    a = p.parse_args()

    root = Path(a.folder)
    files = sorted({f for pat in a.patterns.split(",") for f in root.glob(pat.strip()) if f.is_file()})
    now = time.time()
    rows = []
    for f in files:
        age = (now - f.stat().st_mtime) / 60
        pid = read_pid(f)
        alive = pid_alive(pid) if pid else None
        reasons = []
        if age > a.max_age_min:
            reasons.append(f"오래됨({age:.0f}분)")
        if pid and alive is False:
            reasons.append(f"PID {pid} 없음")
        status = "의심" if reasons else "정상"
        rows.append({"파일": f.name, "경과분": f"{age:.0f}", "PID": pid or "",
                     "프로세스": {True: "있음", False: "없음", None: "-"}[alive],
                     "판정": status, "이유": ", ".join(reasons), "조치": ""})

    for r in rows:
        if r["판정"] == "의심":
            if a.apply:
                q = Path(a.quarantine)
                q.mkdir(parents=True, exist_ok=True)
                dest = q / f"{time.strftime('%Y%m%d_%H%M%S')}_{r['파일']}"
                shutil.move(str(root / r["파일"]), dest)
                r["조치"] = f"격리: {dest}"
            else:
                r["조치"] = "미리보기(--apply 시 격리)"

    with open(a.output, "w", newline="", encoding="utf-8-sig") as fp:
        w = csv.DictWriter(fp, fieldnames=["파일", "경과분", "PID", "프로세스", "판정", "이유", "조치"])
        w.writeheader()
        w.writerows(rows)
    bad = [r for r in rows if r["판정"] == "의심"]
    print(f"검사 {len(rows)}개 / 의심 {len(bad)}개 → {a.output}")
    for r in bad:
        print(f"  [의심] {r['파일']}: {r['이유']} → {r['조치']}")
    if not a.apply and bad:
        print("※ 미리보기입니다. 배치 담당자와 확인 후 --apply 로 격리하세요.")


if __name__ == "__main__":
    main()
