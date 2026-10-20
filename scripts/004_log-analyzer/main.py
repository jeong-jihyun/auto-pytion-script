"""로그 파일 분석·요약 스크립트 (배치/서버 로그용).

형식: '2026-10-01 09:00:01 [LEVEL] 메시지'
- 레벨별(INFO/WARN/ERROR) 개수
- 시간대별 ERROR 개수
- 자주 나오는 ERROR 메시지 상위 N개
결과를 화면에 보여주고, 원하면 요약 파일(--output)로 저장합니다.
"""
import argparse
import re
from collections import Counter
from pathlib import Path

패턴 = re.compile(r"^(\d{4}-\d{2}-\d{2}) (\d{2}):\d{2}:\d{2} \[(\w+)\] (.*)$")


def main():
    p = argparse.ArgumentParser(description="로그 요약")
    p.add_argument("logfile", type=Path)
    p.add_argument("--top", type=int, default=3, help="자주 나온 ERROR 상위 개수")
    p.add_argument("-o", "--output", type=Path, help="요약을 저장할 파일")
    a = p.parse_args()
    레벨, 시간, 오류 = Counter(), Counter(), Counter()
    못읽음 = 0
    for line in a.logfile.read_text(encoding="utf-8").splitlines():
        m = 패턴.match(line)
        if not m:
            못읽음 += 1
            continue
        날짜, 시, lv, msg = m.groups()
        레벨[lv] += 1
        if lv == "ERROR":
            시간[f"{날짜} {시}시"] += 1
            오류[re.sub(r"\d+", "N", msg)] += 1  # 숫자만 다른 메시지는 한 묶음으로
    out = ["== 로그 요약 =="]
    out += [f"{k}: {v}건" for k, v in sorted(레벨.items())]
    out.append("-- 시간대별 ERROR --")
    out += [f"{k}: {v}건" for k, v in sorted(시간.items())]
    out.append(f"-- 자주 나온 ERROR 상위 {a.top} --")
    out += [f"{v}회  {k}" for k, v in 오류.most_common(a.top)]
    out.append(f"형식이 달라 읽지 못한 줄: {못읽음}")
    text = "\n".join(out)
    print(text)
    if a.output:
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
