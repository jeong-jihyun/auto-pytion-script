"""일정 CSV -> 캘린더 파일(.ics) 변환 스크립트.

CSV에 적은 일정을 .ics 파일로 만들면 구글 캘린더·아웃룩·휴대폰 캘린더에서 '가져오기'로 한 번에 넣을 수 있습니다.
입력 열: 제목, 날짜(YYYY-MM-DD), 시작(HH:MM), 종료(HH:MM), 장소, 메모, 반복, 횟수
  - 시작·종료가 비어 있으면 하루 종일 일정이 됩니다.
  - 반복: 매일 / 매주 / 매월 (비우면 반복 없음), 횟수: 반복할 총 횟수
시간은 '현지 시각(타임존 없음)'으로 저장하므로, 가져온 캘린더의 시간대로 보입니다.
"""
import argparse
import csv
import hashlib
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

반복표 = {"매일": "DAILY", "매주": "WEEKLY", "매월": "MONTHLY"}


def 이스케이프(글):
    """ics 규칙: 줄바꿈·쉼표·세미콜론·역슬래시는 앞에 역슬래시를 붙입니다."""
    return (글.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
              .replace("\r\n", "\\n").replace("\n", "\\n"))


def 접기(줄):
    """ics 한 줄은 75바이트가 넘으면 접어야 합니다(다음 줄 맨 앞에 공백)."""
    바이트 = 줄.encode("utf-8")
    if len(바이트) <= 75:
        return 줄
    조각, 현재 = [], b""
    for 글자 in 줄:
        b = 글자.encode("utf-8")
        if len(현재) + len(b) > (75 if not 조각 else 74):
            조각.append(현재.decode("utf-8"))
            현재 = b
        else:
            현재 += b
    조각.append(현재.decode("utf-8"))
    return "\r\n ".join(조각)


def main():
    p = argparse.ArgumentParser(description="일정 CSV를 .ics 로 변환")
    p.add_argument("input", help="일정 CSV")
    p.add_argument("-o", "--output", default="output/schedule.ics")
    p.add_argument("--calendar-name", default="업무 일정")
    p.add_argument("--encoding", default="utf-8-sig")
    a = p.parse_args()

    지금 = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    줄들 = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//auto-pytion-script//ics-maker//KO",
           "CALSCALE:GREGORIAN", f"X-WR-CALNAME:{이스케이프(a.calendar_name)}"]
    개수, 건너뜀 = 0, []
    with open(a.input, newline="", encoding=a.encoding) as fp:
        for 번호, 행 in enumerate(csv.DictReader(fp), start=2):
            try:
                날짜 = datetime.strptime(행["날짜"].strip(), "%Y-%m-%d")
                시작 = (행.get("시작") or "").strip()
                종료 = (행.get("종료") or "").strip()
                제목 = 행["제목"].strip()
                if not 제목:
                    raise ValueError("제목이 비었습니다")
                줄 = ["BEGIN:VEVENT",
                      "UID:" + hashlib.sha1(f"{제목}{행['날짜']}{시작}".encode()).hexdigest()[:20] + "@auto-pytion",
                      f"DTSTAMP:{지금}"]
                if 시작:
                    s = datetime.strptime(시작, "%H:%M")
                    s = 날짜.replace(hour=s.hour, minute=s.minute)
                    e = datetime.strptime(종료, "%H:%M") if 종료 else None
                    e = 날짜.replace(hour=e.hour, minute=e.minute) if e else s + timedelta(hours=1)
                    if e <= s:
                        raise ValueError("종료가 시작보다 빨라요")
                    줄 += [f"DTSTART:{s:%Y%m%dT%H%M%S}", f"DTEND:{e:%Y%m%dT%H%M%S}"]
                else:  # 하루 종일
                    줄 += [f"DTSTART;VALUE=DATE:{날짜:%Y%m%d}",
                          f"DTEND;VALUE=DATE:{날짜 + timedelta(days=1):%Y%m%d}"]
                줄.append("SUMMARY:" + 이스케이프(제목))
                if (행.get("장소") or "").strip():
                    줄.append("LOCATION:" + 이스케이프(행["장소"].strip()))
                if (행.get("메모") or "").strip():
                    줄.append("DESCRIPTION:" + 이스케이프(행["메모"].strip()))
                반복 = (행.get("반복") or "").strip()
                if 반복:
                    if 반복 not in 반복표:
                        raise ValueError(f"반복은 매일/매주/매월 중 하나여야 합니다: {반복}")
                    횟수 = int((행.get("횟수") or "0").strip() or 0)
                    if 횟수 < 1:
                        raise ValueError("반복을 쓰면 횟수(1 이상)도 적어야 합니다")
                    줄.append(f"RRULE:FREQ={반복표[반복]};COUNT={횟수}")
                줄.append("END:VEVENT")
                줄들 += 줄
                개수 += 1
            except (ValueError, KeyError) as e:
                건너뜀.append((번호, str(e)))
    줄들.append("END:VCALENDAR")

    out = Path(a.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    # ics 표준은 줄바꿈이 CRLF 입니다.
    out.write_bytes(("\r\n".join(접기(x) for x in 줄들) + "\r\n").encode("utf-8"))
    print(f"완료: 일정 {개수}개 -> {out}")
    for 번호, 이유 in 건너뜀:
        print(f"  [건너뜀] {번호}번째 줄: {이유}")
    return 0 if 개수 else 1


if __name__ == "__main__":
    sys.exit(main())
