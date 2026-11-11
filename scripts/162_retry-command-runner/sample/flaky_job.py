"""연습용 가짜 배치: 상태 파일에 실행 횟수를 적고, 정해진 횟수까지는 실패합니다."""
import sys
from pathlib import Path

state = Path(sys.argv[1])          # 실행 횟수를 적어 둘 파일
fail_times = int(sys.argv[2])      # 처음 몇 번 실패할지
n = int(state.read_text()) + 1 if state.exists() else 1
state.write_text(str(n))
if n <= fail_times:
    print(f"{n}번째 실행: 연결 실패(가짜)", file=sys.stderr)
    sys.exit(1)
print(f"{n}번째 실행: 전송 완료 120건(가짜)")
