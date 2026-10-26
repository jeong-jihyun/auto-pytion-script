# 119 XML 레코드를 CSV로 펼치기

## 무엇을 하나요?
XML 파일에서 **반복되는 한 건 단위 태그**(예: `<Trade>`)를 찾아 한 줄씩 **CSV 표**로 펼칩니다. 하위 태그는 `부모/자식`, 속성은 `@속성`(하위 태그 속성은 `태그/@속성`) 열이 되고, 같은 태그가 여러 번 나오면 `Tag[2]`처럼 번호를 붙입니다.

## 어떤 업무에 쓰나요?
- 은행·카드사·관공서·타 시스템 연계 XML 파일을 엑셀로 확인
- 전자문서(XML) 데이터 검증 전 표로 변환

## 설치
파이썬 3.8 이상. 설치할 것 없음(표준 xml.etree 사용).

## 실행 예시
```
python3 main.py sample/transactions.xml                       # 1단계: 반복 태그 후보 보기
python3 main.py sample/transactions.xml --record Trade -o output/records.csv
```

## 입력 / 출력 예시
- 입력: XML 파일. 네임스페이스(`xmlns=...`)는 자동으로 떼어 냅니다.
- 출력 CSV 열(샘플): `@id, @type, Time, Amount/@currency, Amount, Counterparty/Name, Counterparty/Bank, Memo, Tag, Tag[2]`

샘플 결과: `<Trade>` 3건, 열 10개. T002는 Bank·Memo가 빈칸, Tag와 Tag[2]에 '비품', '소모품'이 들어갑니다.

## 주의사항
- 레코드 바깥의 값(샘플의 `account`, `date`)은 들어가지 않습니다. 필요하면 엑셀에서 열을 추가하세요.
- 아주 큰 XML(수백 MB)은 메모리를 많이 씁니다. 출처를 모르는 XML은 열기 전에 확인하세요. 샘플은 가짜 거래입니다.
