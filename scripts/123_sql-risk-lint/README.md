# 123 SQL 반영 전 위험 구문 점검

## 무엇을 하나요?
운영 DB에 반영할 `.sql` 파일을 **실행하지 않고 글자만 읽어서** 사고 나기 쉬운 문장을 찾아 줍니다. 주석과 따옴표 안 글자는 먼저 지우고 검사하므로 `-- DELETE ...` 같은 주석에는 속지 않습니다.

| 등급 | 찾는 것 |
|---|---|
| 위험 | WHERE 없는 UPDATE/DELETE, `WHERE 1=1` 뿐인 UPDATE/DELETE, DROP, TRUNCATE, ALTER ... DROP |
| 주의 | 열 이름 없는 INSERT(`INSERT INTO t VALUES ...`), GRANT/REVOKE |
| 참고 | `SELECT *` |

'위험'이 하나라도 있으면 종료 코드 1을 돌려주므로, 반영 절차(배치·CI)에 넣어 자동으로 막을 수 있습니다.

## 어떤 업무에 쓰나요?
- 운영 반영 요청서에 붙은 SQL의 사전 검토(동료 검토 전에 1차 거르기)
- 데이터 보정 스크립트, 월말 정산 보정 SQL 점검

## 설치
파이썬 3.8 이상. 설치할 것 없음.

## 실행 예시
```
python3 main.py sample/release_20261027.sql -o output/sql_lint.csv
python3 main.py 반영폴더/ --encoding cp949      # 폴더 안 *.sql 전부
```

## 입력 / 출력 예시
- 입력: SQL 파일(여러 개·폴더 가능)
- 출력 CSV 열: `파일, 문장번호, 줄, 등급, 규칙, 첫줄`

샘플 결과: 위험 5건(10줄 WHERE 없는 UPDATE, 13줄 WHERE 1=1 DELETE, 15줄 WHERE 없는 DELETE, 21줄 TRUNCATE, 23줄 ALTER DROP COLUMN), 주의 2건, 참고 1건. 문자열 속 `'변경; DROP 아님'`과 주석 속 DELETE는 걸리지 않습니다.

## 주의사항
- 간단한 글자 규칙 검사입니다. PL/SQL 프로시저 본문(BEGIN ... END 안의 `;`), 동적 SQL은 정확히 나누지 못할 수 있습니다.
- '위험'이 없다고 안전하다는 뜻은 아닙니다. 사람 검토와 백업·롤백 계획은 꼭 따로 준비하세요.
- 샘플 SQL은 가짜 테이블입니다.
