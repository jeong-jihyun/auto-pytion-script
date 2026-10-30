"""샘플 lock 폴더를 만듭니다(파일 시각을 일부러 과거로 바꿔 '오래된 파일'을 흉내 냅니다)."""
import os
import time
from pathlib import Path

d = Path(__file__).parent / "sample" / "locks"
d.mkdir(parents=True, exist_ok=True)
now = time.time()
(d / "daily_settle.lock").write_text("999999\n")          # 없는 PID + 오래됨
os.utime(d / "daily_settle.lock", (now - 6 * 3600, now - 6 * 3600))
(d / "this_shell.pid").write_text(f"{os.getpid()}\n")    # 만들 때의 PID (끝나면 사라짐)
(d / "report_job.lock").write_text("")                  # 내용 없음, 방금 생김 → 정상
(d / "eod_close.lock").write_text("1\n")                 # PID 1 은 거의 항상 살아 있음 → 정상
print(f"샘플 생성: {d}")
