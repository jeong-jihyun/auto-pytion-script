# 077 사진 이름을 촬영일시로 바꾸기

## 무엇을 하나요?
폴더 안 사진의 EXIF 촬영 일시를 읽어 `20261020_091500.jpg` 형태로 이름을 바꿉니다. 같은 시각 사진은 `_1`, `_2`를 붙여 겹치지 않게 하고, 무엇을 바꿨는지 CSV 기록을 남깁니다.

## 어떤 업무에 쓰나요?
- 현장 점검 사진, 영수증·증빙 사진, 행사 사진을 날짜순으로 정리할 때.

## 설치
```
pip install -r requirements.txt
```

## 실행 예시
```
python3 main.py sample                       # 미리보기(이름 안 바뀜)
python3 main.py sample --prefix 현장A_         # 앞에 말 붙이기
python3 main.py 내사진폴더 --apply               # 실제로 변경
python3 main.py 내사진폴더 --fallback mtime      # EXIF 없으면 파일 수정시각 사용
```

## 입력 / 출력 예시
```
IMG_0001.jpg → 20261020_091500.jpg (EXIF)
IMG_0002.jpg → 20261020_091500_1.jpg (EXIF)
KakaoTalk_photo.jpg → 20261021_140322.jpg (EXIF)
scan_noexif.jpg → - (촬영일시 없음 → 건너뜀)
```

## 주의사항
- **기본은 미리보기**입니다. `--apply`를 붙여야 실제로 바뀝니다. 처음에는 복사본 폴더로 해 보세요.
- 메신저로 받은 사진은 EXIF가 지워진 경우가 많습니다. 그럴 때 `--fallback mtime`을 쓰면 '받은 시각'이 들어갈 수 있으니 주의하세요.
- HEIC는 Pillow에 HEIF 플러그인이 없으면 읽지 못해 건너뜁니다(미확인).
- 샘플 사진은 16×16 단색 가짜 이미지입니다. 기록 파일은 `output/`에 저장되며 저장소에는 올라가지 않습니다.
