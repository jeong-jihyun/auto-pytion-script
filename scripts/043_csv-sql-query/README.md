# 043 CSV를 SQL로 조회하기

## 무엇을 하나요?
CSV 파일을 임시 데이터베이스(SQLite, 파이썬에 기본 포함)에 넣고 **SQL로 조회**합니다. 피벗이나 VLOOKUP 대신 `GROUP BY`, `JOIN` 을 쓸 수 있습니다.

## 어떤 업무에 쓰나요?
- 엑셀로 열기엔 큰 CSV에서 합계·건수를 뽑을 때
- 두 파일을 이어서(JOIN) 집계할 때 (SQL을 아는 분께 편함)

## 설치
파이썬 3.8 이상. 설치할 것 없음.

## 실행 예시
```
python3 main.py sample/orders.csv sample/customers.csv -q "SELECT c.grade, COUNT(*) AS 건수, SUM(CAST(o.amount AS REAL)) AS 합계 FROM orders o JOIN customers c ON o.customer_id=c.customer_id GROUP BY c.grade"
```

## 입력 / 출력 예시
`grade | 건수 | 합계` → VIP 3건 249000, 일반 2건 60000 처럼 나옵니다.

## 주의사항
- 파일 이름이 테이블 이름입니다(`orders.csv` → `orders`).
- 모든 열이 글자로 들어갑니다. 계산할 때는 `CAST(열 AS REAL)`.
- **SELECT 문만** 실행됩니다. 데이터베이스는 메모리에만 있고 끝나면 사라집니다.
