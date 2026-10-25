"""로그 속 자바·파이썬 예외(스택트레이스)를 '같은 원인'끼리 묶어 집계하는 스크립트.

생각의 흐름:
  1) 스택트레이스는 여러 줄입니다. 예외 이름 줄(예: java.lang.NullPointerException: ...)에서
     시작해, 뒤따르는 '\tat ...' / 'Caused by:' / 'File "...", line N' 줄까지를 한 덩어리로 봅니다.
  2) 덩어리마다 '예외 종류 + 처음 나오는 우리 코드 위치(--package 로 지정)'를 묶음 키로 씁니다.
     메시지 안의 숫자·ID는 매번 달라지므로 키에 넣지 않습니다.
  3) 묶음별 발생 횟수, 처음·마지막 발생 시각, 대표 메시지를 CSV로 저장합니다.
     → 오류 1000줄 대신 '원인 5가지'로 보고할 수 있습니다.
"""
import argparse
import csv
import re
from collections import OrderedDict
from pathlib import Path

TS = re.compile(r"^(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2})")
JAVA_EX = re.compile(r"((?:[a-zA-Z_$][\w$]*\.)+[A-Z][\w$]*(?:Exception|Error|Throwable))(?::\s*(.*))?")
PY_EX = re.compile(r"^([A-Z]\w*(?:Error|Exception|Exit|Interrupt))(?::\s*(.*))?$")
JAVA_AT = re.compile(r"^\s+at\s+([\w$.<>]+)\(([^)]*)\)")
PY_FILE = re.compile(r'^\s+File "([^"]+)", line (\d+), in (\S+)')


def parse(lines, package):
    """로그 줄 목록에서 예외 덩어리(dict) 목록을 만듭니다."""
    blocks, cur, last_ts, in_py = [], None, "", False
    for line in lines:
        line = line.rstrip("\n")
        m = TS.match(line)
        if m:
            last_ts = m.group(1)
        if line.startswith("Traceback (most recent call last)"):
            in_py = True
            cur = {"ts": last_ts, "type": "", "msg": "", "frames": [], "lang": "python"}
            blocks.append(cur)
            continue
        if cur is not None and cur["lang"] == "python" and in_py:
            f = PY_FILE.match(line)
            if f:
                cur["frames"].append(f"{f.group(1)}:{f.group(2)} {f.group(3)}")
                continue
            if line.startswith("    "):
                continue  # 소스 코드 줄
            e = PY_EX.match(line.strip())
            if e:
                cur["type"], cur["msg"] = e.group(1), e.group(2) or ""
                in_py = False
                continue
        at = JAVA_AT.match(line)
        if at and cur is not None and cur["lang"] == "java":
            cur["frames"].append(at.group(1))
            continue
        if line.strip().startswith("Caused by:") and cur is not None:
            e = JAVA_EX.search(line)
            if e:
                cur["cause"] = e.group(1)  # 근본 원인은 따로 기록
            continue
        e = JAVA_EX.search(line)
        if e and ("Exception" in line or "Error" in line):
            cur = {"ts": last_ts, "type": e.group(1), "msg": (e.group(2) or "").strip(),
                   "frames": [], "lang": "java"}
            blocks.append(cur)
            continue
    for b in blocks:
        mine = [f for f in b["frames"] if package and package in f]
        b["where"] = (mine or b["frames"] or ["(위치 없음)"])[0 if b["lang"] == "java" else -1]
        if b["lang"] == "python" and mine:
            b["where"] = mine[-1]  # 파이썬은 마지막 프레임이 실제 오류 위치
    return [b for b in blocks if b["type"]]


def main():
    p = argparse.ArgumentParser(description="스택트레이스 묶음 집계")
    p.add_argument("logs", nargs="+", type=Path, help="로그 파일(여러 개 가능)")
    p.add_argument("--package", default="", help="우리 코드 구분 글자(예: com.mycorp 또는 app/)")
    p.add_argument("--encoding", default="utf-8")
    p.add_argument("-o", "--output", type=Path, default=Path("output/exceptions.csv"))
    a = p.parse_args()

    groups = OrderedDict()
    total = 0
    for path in a.logs:
        with path.open(encoding=a.encoding, errors="replace") as fp:
            for b in parse(fp, a.package):
                total += 1
                key = (b["type"], b.get("cause", ""), b["where"])
                g = groups.setdefault(key, {"count": 0, "first": b["ts"], "last": b["ts"],
                                            "msg": b["msg"], "file": path.name})
                g["count"] += 1
                g["last"] = b["ts"] or g["last"]

    rows = sorted(groups.items(), key=lambda kv: -kv[1]["count"])
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["순위", "예외", "근본원인(Caused by)", "발생위치", "횟수", "처음", "마지막", "대표메시지", "파일"])
        for i, ((t, c, where), g) in enumerate(rows, 1):
            w.writerow([i, t, c, where, g["count"], g["first"], g["last"], g["msg"][:200], g["file"]])
    print(f"예외 {total}건 → 원인 묶음 {len(rows)}개 → {a.output}")
    for i, ((t, c, where), g) in enumerate(rows[:10], 1):
        extra = f" (원인 {c})" if c else ""
        print(f"  {i}. {t}{extra} @ {where} : {g['count']}회")


if __name__ == "__main__":
    main()
