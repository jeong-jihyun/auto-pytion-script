"""공개 웹페이지 제목·링크 수집 스크립트 (robots.txt 준수).

주소 목록을 받아서 각 페이지의 제목, 설명(meta description), 링크 개수, 링크 목록을 CSV로 저장합니다.
예의 바르게 수집하기 위해 다음을 지킵니다.
  1. 페이지마다 해당 사이트의 robots.txt 를 먼저 확인하고, 막혀 있으면 가져오지 않습니다.
  2. 요청 사이에 쉬는 시간(--delay)을 둡니다. (기본 2초)
  3. 누구인지 알 수 있는 User-Agent 를 보냅니다. (--user-agent 에 연락처를 넣어 주세요)
  4. 로그인이 필요한 페이지, CAPTCHA 우회, 개인정보 수집은 하지 않습니다. 공개 페이지만 대상으로 합니다.
robots.txt 를 읽을 수 없는 경우(서버 오류·접속 실패)에는 안전하게 '수집하지 않음'으로 처리합니다.
※ 사이트의 이용약관은 코드가 확인해 줄 수 없습니다. 수집 전에 꼭 직접 읽어 보세요.
표준 라이브러리만 사용합니다.
"""
import argparse
import csv
import sys
import time
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser


class 페이지분석(HTMLParser):
    """HTML에서 <title>, meta description, <a href> 를 모읍니다."""

    def __init__(self, 기준주소):
        super().__init__()
        self.기준 = 기준주소
        self.제목 = ""
        self.설명 = ""
        self.링크 = []
        self._제목안 = False

    def handle_starttag(self, tag, attrs):
        속성 = dict(attrs)
        if tag == "title":
            self._제목안 = True
        elif tag == "meta" and (속성.get("name") or "").lower() == "description":
            self.설명 = (속성.get("content") or "").strip()
        elif tag == "a" and 속성.get("href"):
            주소 = urljoin(self.기준, 속성["href"])
            if urlparse(주소).scheme in ("http", "https") and 주소 not in self.링크:
                self.링크.append(주소)

    def handle_endtag(self, tag):
        if tag == "title":
            self._제목안 = False

    def handle_data(self, data):
        if self._제목안:
            self.제목 += data


def 로봇_확인기(주소, 에이전트, 캐시, 제한시간):
    """사이트별 robots.txt 를 한 번만 읽어서 (허용 여부, 이유) 를 돌려줍니다."""
    u = urlparse(주소)
    기본 = f"{u.scheme}://{u.netloc}"
    if 기본 not in 캐시:
        rp = RobotFileParser()
        try:
            요청 = urllib.request.Request(기본 + "/robots.txt", headers={"User-Agent": 에이전트})
            with urllib.request.urlopen(요청, timeout=제한시간) as 응답:
                rp.parse(응답.read().decode("utf-8", "replace").splitlines())
            캐시[기본] = (rp, "")
        except urllib.error.HTTPError as e:
            if e.code in (404, 410):      # robots.txt 가 아예 없으면 제한이 없다는 뜻
                rp.parse([])
                캐시[기본] = (rp, "")
            else:                         # 401/403/5xx 는 조심스럽게 '불가'로 봅니다
                캐시[기본] = (None, f"robots.txt 응답 코드 {e.code}")
        except Exception as e:
            캐시[기본] = (None, f"robots.txt 를 읽지 못함: {e}")
    rp, 이유 = 캐시[기본]
    if rp is None:
        return False, 이유
    if not rp.can_fetch(에이전트, 주소):
        return False, "robots.txt 가 이 주소의 수집을 막음"
    return True, ""


def main():
    p = argparse.ArgumentParser(description="공개 웹페이지 제목·링크 수집 (robots.txt 준수)")
    p.add_argument("urls", help="주소 목록 txt (한 줄에 하나, #은 주석)")
    p.add_argument("-o", "--output", default="output/pages.csv")
    p.add_argument("--delay", type=float, default=2.0, help="요청 사이 쉬는 시간(초). 기본 2")
    p.add_argument("--timeout", type=float, default=10.0, help="응답 기다리는 시간(초)")
    p.add_argument("--max-links", type=int, default=20, help="CSV에 적을 링크 최대 개수")
    p.add_argument("--max-bytes", type=int, default=2_000_000, help="페이지 최대 크기(바이트)")
    p.add_argument("--user-agent", default="auto-pytion-script/1.0 (contact: your-email@example.com)",
                   help="사이트에 알려 줄 이름. 영문만 가능. 본인 연락처(이메일)로 바꿔 주세요")
    a = p.parse_args()
    if not a.user_agent.isascii():
        print("[오류] --user-agent 는 영문·숫자·기호만 쓸 수 있어요(HTTP 규칙). 예: \"my-script/1.0 (contact: me@example.com)\"")
        return 1

    주소들 = [x.strip() for x in Path(a.urls).read_text(encoding="utf-8").splitlines()
              if x.strip() and not x.strip().startswith("#")]
    캐시, 행들, 마지막요청 = {}, [], 0.0
    for 주소 in 주소들:
        if urlparse(주소).scheme not in ("http", "https"):
            행들.append([주소, "건너뜀(http/https 만 가능)", "", "", 0, ""])
            continue
        허용, 이유 = 로봇_확인기(주소, a.user_agent, 캐시, a.timeout)
        if not 허용:
            행들.append([주소, f"수집 안 함({이유})", "", "", 0, ""])
            print(f"  [차단] {주소} - {이유}")
            continue
        쉼 = a.delay - (time.time() - 마지막요청)
        if 쉼 > 0:
            time.sleep(쉼)
        마지막요청 = time.time()
        try:
            요청 = urllib.request.Request(주소, headers={"User-Agent": a.user_agent})
            with urllib.request.urlopen(요청, timeout=a.timeout) as 응답:
                종류 = 응답.headers.get("Content-Type", "")
                if "html" not in 종류.lower():
                    행들.append([주소, f"건너뜀(HTML 아님: {종류})", "", "", 0, ""])
                    continue
                원문 = 응답.read(a.max_bytes).decode(응답.headers.get_content_charset() or "utf-8", "replace")
            분석 = 페이지분석(응답.geturl())
            분석.feed(원문)
            행들.append([주소, "성공", " ".join(분석.제목.split()), 분석.설명, len(분석.링크),
                      "\n".join(분석.링크[:a.max_links])])
            print(f"  [성공] {주소} -> {' '.join(분석.제목.split())!r}")
        except Exception as e:
            행들.append([주소, f"실패({e})", "", "", 0, ""])
            print(f"  [실패] {주소}: {e}")

    out = Path(a.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["주소", "상태", "제목", "설명", "링크개수", "링크목록"])
        w.writerows(행들)
    성공 = sum(1 for r in 행들 if r[1] == "성공")
    print(f"완료: 주소 {len(주소들)}개 중 성공 {성공}개 -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
