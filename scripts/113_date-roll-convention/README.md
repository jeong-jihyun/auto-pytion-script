# 113 휴일 날짜 조정(영업일 규칙)

## 무엇을 하나요?
지급일·결제일이 **주말이나 휴일**이면 금융에서 쓰는 4가지 규칙으로 옮긴 날짜를 한 표에 보여 줍니다.

| 규칙 | 뜻 |
|---|---|
| following | 다음 영업일로 미룸 |
| preceding | 앞 영업일로 당김 |
| modified_following | 미루되 달이 바뀌면 앞으로 당김 (이자 지급에 많이 씀) |
| modified_preceding | 당기되 달이 바뀌면 뒤로 미룸 |

## 어떤 업무에 쓰나요?
- 이자·쿠폰 지급일, 카드·대금 결제일, 급여일 스케줄 확정
- 시스템 날짜 조정 로직 결과를 검증할 때 비교용

## 설치
파이썬 3.8 이상. 설치할 것 없음.

## 실행 예시
```
python3 main.py sample/dates.csv --holidays sample/holidays.txt -o output/rolled_dates.csv
python3 main.py sample/dates.csv --holidays sample/holidays.txt --rule modified_following
```

## 입력 / 출력 예시
- 날짜 CSV: `이름, 날짜(YYYY-MM-DD)` / 휴일 파일: 한 줄에 날짜 하나(`#` 뒤는 메모)
- 출력 CSV 열: `이름, 원래날짜, 요일, 영업일여부, 규칙별 조정 날짜(요일)`

샘플 결과: 2026-10-31(토) 결제일은 following이면 11-02(월)로 달이 바뀌므로 modified_following에서는 10-30(금)이 됩니다. 11-30(가상 휴일)은 following이면 12-01, modified_following이면 11-27(금).

## 주의사항
- 실제 공휴일·대체공휴일은 들어 있지 않습니다. 회사·거래소 달력에 맞는 휴일 파일을 직접 만드세요.
- 샘플 휴일 파일의 11-30은 설명을 위한 가상 휴일입니다.
