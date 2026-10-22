"""HTML 파일의 표(<table>)를 CSV 로 바꾸는 스크립트.

웹 화면을 '다른 이름으로 저장'한 .html 파일이나, 시스템이 내보낸 HTML 보고서 안의
표를 찾아 표마다 CSV 파일 하나로 저장합니다. 인터넷에 접속하지 않고 내 컴퓨터의 파일만 읽습니다.
표준 라이브러리(html.parser)만 사용합니다.
"""
import argparse
import csv
from html.parser import HTMLParser
from pathlib import Path


class TableParser(HTMLParser):
    """HTML 을 훑으면서 표(table) -> 줄(tr) -> 칸(td/th) 글자를 모읍니다."""

    def __init__(self):
        super().__init__()
        self.tables = []      # 완성된 표들
        self._table = None    # 지금 읽는 표 (줄 목록)
        self._row = None      # 지금 읽는 줄 (칸 목록)
        self._cell = None     # 지금 읽는 칸 (글자 조각 목록)
        self._depth = 0       # 표 안에 표가 있을 때를 대비한 깊이

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self._depth += 1
            if self._depth == 1:
                self._table = []
        elif self._depth == 1:
            if tag == "tr":
                self._row = []
            elif tag in ("td", "th"):
                self._cell = []
            elif tag == "br" and self._cell is not None:
                self._cell.append(" ")

    def handle_endtag(self, tag):
        if tag == "table":
            if self._depth == 1 and self._table is not None:
                self.tables.append(self._table)
                self._table = None
            self._depth = max(self._depth - 1, 0)
        elif self._depth == 1:
            if tag in ("td", "th") and self._cell is not None and self._row is not None:
                self._row.append(" ".join("".join(self._cell).split()))
                self._cell = None
            elif tag == "tr" and self._row is not None and self._table is not None:
                if self._row:
                    self._table.append(self._row)
                self._row = None

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)


def main():
    p = argparse.ArgumentParser(description="HTML 표를 CSV 로")
    p.add_argument("input", type=Path, help="HTML 파일")
    p.add_argument("-o", "--outdir", type=Path, default=Path("output"))
    p.add_argument("--encoding", default="utf-8", help="HTML 파일 인코딩(기본 utf-8, 한글 구형은 cp949)")
    a = p.parse_args()

    parser = TableParser()
    parser.feed(a.input.read_text(encoding=a.encoding, errors="replace"))
    if not parser.tables:
        print("표(<table>)를 찾지 못했습니다.")
        return
    a.outdir.mkdir(parents=True, exist_ok=True)
    for i, rows in enumerate(parser.tables, start=1):
        path = a.outdir / f"{a.input.stem}_table{i}.csv"
        with path.open("w", newline="", encoding="utf-8-sig") as fp:
            csv.writer(fp).writerows(rows)
        print(f"표 {i}: {len(rows)}줄 x 최대 {max(len(r) for r in rows)}칸 -> {path}")


if __name__ == "__main__":
    main()
