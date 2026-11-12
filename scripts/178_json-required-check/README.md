# 178 JSON 필수 키·자료형 검사

## 무엇을 하나요?
API 응답·연동 전문·설정 같은 **JSON 파일 여러 개**가 약속한 모양을 지키는지 검사합니다. 규칙 파일에 적은 경로마다 **필수 키, 자료형, 허용값, 최소·최대, 길이, 정규식**을 확인하고, 깨진 JSON도 알려 줍니다. 외부 패키지 없이 돌아가는 가벼운 검사기입니다.

## 어떤 업무에 쓰나요?
- 대외기관·다른 팀과 연동할 때 받은 전문 샘플 사전 점검
- 연동 장애 때 "어느 파일 어느 키가 약속과 다른지" 빨리 찾기
- 배포 전 설정 JSON에 필수 항목이 다 있는지 확인 (009번은 CSV용, 이 스크립트는 JSON용)

## 생각의 흐름
경로는 점(`.`)으로 내려가고 목록 안은 `[]` 로 씁니다. 예: `body.items[].qty` 는 items 목록의 **원소마다** qty를 봅니다. 파이썬은 `true` 를 정수로도 취급하는 함정이 있어, integer/number 검사에서 참·거짓 값은 따로 걸러 냅니다.

## 설치
파이썬 3.8 이상. 추가 설치 없음.

## 실행 예시
```bash
python main.py "sample/responses/*.json" --rules sample/rules.json
python main.py resp1.json resp2.json --rules rules.json -o out/check.csv
```

## 규칙 파일 예시
```json
{
  "header.trx_code": {"type": "string", "required": true, "enum": ["ORD", "CXL", "MOD"]},
  "header.trx_id":   {"type": "string", "required": true, "pattern": "T\\d{8}"},
  "body.items[].qty": {"type": "integer", "required": true, "min": 1},
  "body.memo":       {"type": ["string", "null"]}
}
```
- type: `string` `integer` `number` `boolean` `array` `object` `null` (여러 개는 목록으로)
- 그 밖: `required` `enum` `min` `max` `max_len` `pattern`(전체 일치)

## 출력 예시
```
파일 4개 검사: 통과 1개, 문제 13건
  bad_002.json | header.trx_code | 허용값 ['ORD', 'CXL', 'MOD'] 이 아님: 'BUY'
  bad_002.json | body.items[0].qty | 자료형이 integer 이어야 하는데 str ("5")
  bad_002.json | body.items[2].qty | 자료형이 integer 이어야 하는데 bool (true)
  bad_003.json | body.items | 목록([])이어야 함
  broken_004.json | (파일) | JSON으로 읽을 수 없음: ...
```
`out/json_check.csv` : 파일, 위치, 문제

## 주의사항
- JSON Schema 표준 전체를 지원하지 않습니다. 복잡한 조건(조건부 필수 등)은 jsonschema 패키지를 쓰세요.
- 규칙에 없는 **추가 키**는 검사하지 않습니다.
- 실제 고객정보가 든 전문은 036번(개인정보 마스킹)으로 가린 뒤 공유하세요.
