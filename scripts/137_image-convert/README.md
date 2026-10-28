# 137 이미지 형식 일괄 변환(jpg/png/webp)

## 무엇을 하나요?
폴더(하위 폴더 포함) 안의 이미지를 **jpg / png / webp** 중 원하는 형식으로 한꺼번에 바꿉니다.
- 투명 PNG → JPG: 투명 부분이 검게 변하지 않게 흰 배경(`--bg`)을 깔아 줍니다.
- 휴대폰 사진의 회전 정보(EXIF)대로 바로 세워 저장합니다.
- **기본은 미리보기**입니다. `--apply` 를 붙여야 실제로 저장합니다.
- 원본은 지우거나 덮어쓰지 않습니다. 결과는 출력 폴더에 같은 하위 폴더 구조로 저장합니다.

## 어떤 업무에 쓰나요?
- 'JPG만 업로드 가능'한 그룹웨어·전자결재에 스캔 이미지 올리기
- 홈페이지·문서용 이미지를 WEBP로 바꿔 용량 줄이기

## 설치
```
pip install -r requirements.txt     # Pillow
```

## 실행 예시
```
python3 main.py sample/images --to jpg -o converted_out             # 미리보기
python3 main.py sample/images --to jpg -o converted_out --apply     # 실제 저장
python3 main.py sample/images --to webp --quality 75 -o converted_out --apply
python3 main.py sample/images --to png --from bmp,gif -o converted_out --apply
```

## 출력 예시
```
  건너뜀(이미 jpg): sample/images/already.jpg
  변환: sample/images/logo_transparent.png → converted_out/logo_transparent.jpg
  변환: sample/images/receipt.bmp → converted_out/receipt.jpg
  변환: sample/images/sub/gray.png → converted_out/sub/gray.jpg
변환 3개, 건너뜀 1개, 실패 0개
용량: 원본 ...KB → 결과 ...KB
```

## 주의사항
- 출력 폴더에 같은 이름 파일이 있으면 건너뜁니다(`--overwrite` 로만 덮어씀).
- 움직이는 GIF는 첫 장면만 저장됩니다.
- jpg·webp 는 손실 압축이라 `--quality` 를 너무 낮추면 글자가 흐려집니다(영수증은 85 이상 권장).
- 크기 줄이기는 014(이미지 리사이즈)를 함께 쓰세요.
