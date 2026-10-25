"""샘플 PDF 4개(글자 있는 것, 빈 쪽, 암호, 깨진 파일)를 sample/ 에 만드는 보조 스크립트."""
from pathlib import Path
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

here = Path(__file__).with_name("sample")
here.mkdir(exist_ok=True)


def page_with_text(w, text):
    page = w.add_blank_page(width=595, height=842)
    font = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"),
                             NameObject("/BaseFont"): NameObject("/Helvetica")})
    page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})})
    s = DecodedStreamObject()
    s.set_data(f"BT /F1 14 Tf 72 760 Td ({text}) Tj ET".encode())
    page[NameObject("/Contents")] = w._add_object(s)


w = PdfWriter()
for i in range(3):
    page_with_text(w, f"Monthly report page {i + 1} - sample text for inventory test")
w.add_metadata({"/Title": "Monthly Report"})
w.write(here / "report.pdf")
w = PdfWriter()
w.add_blank_page(width=595, height=842)
w.add_blank_page(width=595, height=842)
w.write(here / "scan_like.pdf")
w = PdfWriter()
page_with_text(w, "secret")
w.encrypt(user_password="1234", owner_password="owner")
w.write(here / "locked.pdf")
(here / "broken.pdf").write_bytes(b"%PDF-1.4 this is not a real pdf")
print("샘플 PDF 생성 완료")
