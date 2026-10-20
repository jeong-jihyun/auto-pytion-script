# PDF 병합·분할·텍스트 추출

## 무엇을 하나요?
명령 세 가지가 있습니다.
- `merge` : 폴더 안 PDF를 이름순으로 하나로 합칩니다.
- `split` : PDF를 N쪽씩, 또는 `1-2,3,5-` 처럼 쪽 범위별로 나눕니다.
- `text`  : PDF 안의 글자를 txt로 뽑습니다.

## 어떤 업무에 쓰나요?
여러 증빙 PDF를 한 파일로 묶어 제출, 긴 보고서를 부서별로 쪼개 배포, PDF 내용을 검색하기 위한 텍스트 추출.

## 설치
```bash
pip install -r requirements.txt
```

## 실행 예시
```bash
python3 main.py merge sample -o output/merged.pdf
python3 main.py split output/merged.pdf --ranges 1-2,3,5- -o output/split
python3 main.py split sample/b_notice.pdf --pages-per-file 2 -o output/split2
python3 main.py text output/merged.pdf -o output/text.txt
```

## 입력 / 출력 예시
- 입력: `sample/a_report.pdf`(2쪽) + `sample/b_notice.pdf`(3쪽)
- merge 결과: 5쪽짜리 `merged.pdf`
- split `--ranges 1-2,3,5-` 결과: `merged_part01_p1-2.pdf`, `merged_part02_p3-3.pdf`, `merged_part03_p5-5.pdf`
- text 결과: 쪽마다 `===== 1쪽 =====` 머리말과 글자가 들어간 txt

## 주의사항
- 원본 PDF는 바꾸지 않고, 항상 새 파일을 만듭니다.
- **스캔한 이미지 PDF는 글자가 없어서 text 로 뽑히지 않습니다.** (OCR 기능은 없음. 글자 없는 쪽이 있으면 알려 줍니다.)
- 비밀번호가 걸린 PDF는 처리하지 못하고 오류 메시지를 보여 줍니다.
- 없는 쪽 번호를 쓰면 아무것도 만들지 않고 오류를 알려 줍니다.

## 테스트 상태
2026-10-20, 파이썬 3.13 에서 sample 데이터로 실제 실행해 동작을 확인했습니다. 병합·분할(범위/개수)·텍스트 추출·잘못된 범위 오류까지 확인했습니다. 샘플 PDF는 영문 텍스트뿐이라 **한글 PDF의 글자 추출, 스캔 PDF, 암호 PDF는 시험하지 못했습니다.**
