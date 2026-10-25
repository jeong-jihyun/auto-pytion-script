"""비교용 샘플 엑셀 두 개(sample/old.xlsx, sample/new.xlsx)를 만드는 보조 스크립트."""
from pathlib import Path
from openpyxl import Workbook

here = Path(__file__).with_name("sample")
here.mkdir(exist_ok=True)
for name, rows, extra in [
    ("old.xlsx", [["품목", "수량", "단가", "금액"], ["볼펜", 10, 500, "=B2*C2"], ["노트", 5, 1200, "=B3*C3"]], False),
    ("new.xlsx", [["품목", "수량", "단가", "금액"], ["볼펜", 12, 500, "=B2*C2"], ["노트", 5, 1300, "=B3*C3"], ["형광펜", 3, 900, "=B4*C4"]], True),
]:
    wb = Workbook()
    ws = wb.active
    ws.title = "주문"
    for r in rows:
        ws.append(r)
    if extra:
        wb.create_sheet("메모")["A1"] = "단가 인상 반영"
    wb.save(here / name)
print("샘플 생성 완료")
