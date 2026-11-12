"""연습용 폴더를 만듭니다. 맥에서 온 것처럼 이름을 NFD(자모 분리)로 저장합니다.

git 은 OS에 따라 NFD 이름을 바꿔 버릴 수 있어서, 샘플 파일 대신 이 스크립트로 만듭니다.
실행: python sample/make_sample.py  → sample_mac_files/ 폴더가 생깁니다.
"""
import os
import unicodedata

base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sample_mac_files")
nfd = lambda s: unicodedata.normalize("NFD", s)
os.makedirs(os.path.join(base, nfd("회의자료")), exist_ok=True)
files = [nfd("주간보고서.docx"), nfd("정산내역_11월.xlsx"), "readme.txt",
         os.path.join(nfd("회의자료"), nfd("발표.pptx")), "견적서.pdf", nfd("견적서.pdf")]
for f in files:
    with open(os.path.join(base, f), "w", encoding="utf-8") as fp:
        fp.write("샘플\n")
print("만들었습니다:", os.path.normpath(base))
