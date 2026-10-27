# 125 이미지 여러 장을 PDF 한 파일로

## 무엇을 하나요?
폴더 안의 이미지(jpg, png, bmp, gif, tif, webp)를 **이름 순서대로**(img2가 img10보다 앞) PDF 한 파일로 묶습니다.
- 휴대폰 사진의 회전 정보(EXIF)를 반영해 바로 세웁니다.
- 투명 배경 PNG는 흰 바탕으로 바꿉니다.
- `--page a4`를 주면 A4 종이 안에 여백을 두고 가운데 배치합니다(인쇄·제출용).

## 어떤 업무에 쓰나요?
- 영수증·증빙 사진을 경비 신청용 PDF 한 파일로 만들 때
- 스캔한 계약서·서류 낱장 이미지를 한 문서로 합칠 때

## 설치
```
pip install -r requirements.txt   # Pillow
```

## 실행 예시
```
python3 main.py sample/images -o output/receipts.pdf
python3 main.py sample/images -o output/receipts_a4.pdf --page a4 --margin 60
```

## 입력 / 출력 예시
- 입력: 이미지 폴더 (샘플: `receipt1.jpg, receipt2.jpg, receipt3.jpg(회전 정보 있음), receipt10.png(투명)`, 이미지가 아닌 `memo.txt`는 무시)
- 출력: PDF 1개. 샘플 결과 4쪽, 순서 receipt1 → 2 → 3 → 10, receipt3은 세로로 바로 세워짐.

## 주의사항
- 같은 이름의 PDF가 있으면 **덮어쓰지 않고 멈춥니다**. 덮어쓰려면 `--overwrite`.
- 이미지를 메모리에 모두 올려서 만드므로, 큰 사진 수백 장은 나눠서 만드세요(014 이미지 리사이즈로 먼저 줄이면 좋습니다).
- 글자 인식(OCR)은 하지 않습니다. PDF 안 글자는 검색되지 않습니다.
- 샘플 이미지는 가짜로 그린 그림입니다.
