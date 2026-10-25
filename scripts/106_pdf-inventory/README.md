# 106 PDF 목록·쪽수 정리

## 무엇을 하나요?
폴더 안 PDF마다 **쪽수, 크기, 암호 여부, 제목, 만든 프로그램, 글자 유무** 를 한 표로 정리합니다. 앞쪽에 글자가 거의 없으면 '스캔본(이미지) 의심'으로 표시해 OCR 대상을 고를 수 있습니다. 깨진 파일은 '열기 실패'로 적고 계속 진행합니다.

## 어떤 업무에 쓰나요?
- 계약서·증빙 PDF 보관 현황 정리, 인쇄량(총 쪽수) 예상
- 검색 안 되는 스캔 PDF, 암호 걸린 PDF 골라내기

## 설치
```
pip install -r requirements.txt
```

## 실행 예시
```
python3 make_sample.py                 # 샘플 PDF 4개 만들기(처음 한 번)
python3 main.py sample -o output/pdf_inventory.csv
python3 main.py 계약서 --recursive
```

## 입력 / 출력 예시
- 출력 CSV 열: `파일, 크기KB, 쪽수, 암호, 제목, 만든프로그램, 글자, 비고`

샘플 결과: PDF 4개, 총 5쪽, 암호 1개 — report.pdf 3쪽 글자 있음, scan_like.pdf 2쪽 스캔본 의심, locked.pdf 암호 필요, broken.pdf 열기 실패.

## 주의사항
- 암호를 풀려고 시도하지 않습니다(빈 암호만 확인). 암호 파일은 쪽수가 비어 있습니다.
- 글자 유무는 앞 2쪽만 봅니다(`--check-pages`로 변경). PDF 병합·분할은 012 스크립트를 쓰세요.
- 샘플 PDF는 직접 만든 가짜 파일입니다.
