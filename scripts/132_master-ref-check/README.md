# 132 마스터 코드 참조 점검(ERP 업로드 전 확인)

## 무엇을 하나요?
주문·전표 CSV에 적힌 거래처코드·품목코드 같은 코드가 **마스터에 실제로 있는지**, **사용중지 코드는 아닌지**, **거래일이 코드의 유효기간 안인지**를 줄마다 점검합니다.

문제 종류: `없음`(마스터에 없음), `사용중지`, `기간외`(유효기간 밖), `빈값`

## 어떤 업무에 쓰나요?
- ERP 일괄 업로드 전에 '마스터에 없는 코드' 오류를 미리 걸러낼 때
- 시스템 이관(데이터 마이그레이션) 때 참조 무결성 확인

## 설치
파이썬 3.8 이상. 설치할 것 없음.

## 실행 예시
```
python3 main.py sample/orders.csv --rules sample/rules.json -o output/ref_issues.csv
python3 main.py sample/orders.csv --rules sample/rules.json --ignore-case --allow-blank 품목코드
```

## 규칙 파일(rules.json) 쓰는 법
```json
{
  "거래처코드": {"master": "vendor_master.csv", "key": "코드",
                "status_col": "사용여부", "active": ["Y"],
                "valid_from": "시작일", "valid_to": "종료일", "date_col": "거래일"},
  "품목코드":  {"master": "item_master.csv", "key": "품목코드", "status_col": "사용", "active": ["Y"]}
}
```
- 바깥 키: 거래 CSV에서 점검할 열 이름
- master: 마스터 CSV 경로(규칙 파일 위치 기준), key: 마스터의 코드 열
- status_col/active: 사용여부 열과 '사용 중'으로 볼 값(없으면 생략)
- valid_from/valid_to/date_col: 유효기간 열과 거래 CSV의 날짜 열(없으면 생략, 날짜는 YYYY-MM-DD)

## 출력 예시
```
행번호,열,코드,문제,설명
3,거래처코드,V002,사용중지,사용여부=N
4,거래처코드,V003,기간외,"거래일=2026-10-21, 유효 2026-11-01~"
6,거래처코드,v001,없음,마스터에 없는 코드     ← --ignore-case 를 주면 통과
7,품목코드,,빈값,코드가 비어 있음             ← --allow-blank 품목코드 로 허용 가능
```
행번호는 엑셀에서 보이는 줄 번호(머리글이 1행)입니다.

## 주의사항
- 앞뒤 공백은 자동으로 지우고 비교합니다.
- 마스터에 같은 코드가 두 번 있으면 아래쪽 줄을 씁니다.
- 샘플 코드·거래처는 가짜입니다.
