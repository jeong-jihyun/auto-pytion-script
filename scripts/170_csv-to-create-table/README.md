# 170 CSV로 CREATE TABLE 문 만들기

## 무엇을 하나요?
CSV의 값을 모두 훑어 열마다 **자료형(정수·소수·날짜·일시·문자열)과 길이**를 추정하고, DB에 표를 만드는 **CREATE TABLE 문**을 만듭니다. PostgreSQL·MySQL·Oracle·SQLite 문법을 고를 수 있고, 한글 열 이름을 영문으로 바꾸면서 원래 이름은 주석(COMMENT)으로 남깁니다. **SQL 파일만 만들고 DB에 실행하지는 않습니다.**

## 어떤 업무에 쓰나요?
- 엑셀·CSV로 받은 데이터를 DB(스테이징 테이블)에 올리기 전 표 만들기
- ERP 이관·데이터 마이그레이션 때 임시 테이블 정의서 초안
- 094번(CSV → INSERT 문)과 함께 쓰면 표 만들기부터 데이터 넣기까지 SQL로 준비

## 추정 규칙
| 값 모양 | 자료형 |
|---|---|
| 모두 정수(쉼표 허용) | INTEGER, 21억 넘으면 BIGINT |
| 소수 포함 | DECIMAL(전체자리+2, 소수자리) |
| 모두 날짜(2026-11-11, 2026/11/11, 2026.11.11) | DATE |
| 모두 날짜+시각 | TIMESTAMP (MySQL은 DATETIME) |
| 그 밖 | VARCHAR(가장 긴 길이 × 1.5, 최소 10) |

- 앞자리가 0인 숫자(우편번호 04524, 사번 00123)는 0이 사라지지 않게 **문자열**로 둡니다.
- 빈칸이 없으면 NOT NULL, 값이 모두 다르고 이름이 ID·코드·번호·no로 끝나면 **기본키 후보**로 넣습니다.
- 20261111처럼 8자리 숫자 날짜는 정수로 잡힙니다. 먼저 026번 날짜 형식 통일로 바꿔 두세요.

## 설치
파이썬 3.8 이상. 추가 설치 없음.

## 실행 예시
```bash
python main.py sample/customers.csv                                   # PostgreSQL, out/customers.sql
python main.py sample/customers.csv -d oracle -t TB_CUSTOMER --rename sample/rename.txt
python main.py sample/customers.csv -d mysql --rename "고객번호=cust_no,고객명=cust_name"
```
`rename.txt` 는 `한글=영문` 을 한 줄에 하나씩 적습니다.

## 출력 예시
```
[oracle] TB_CUSTOMER: 열 9개, 4행 확인 → out/TB_CUSTOMER.sql
  우편번호 → zip_code  VARCHAR2(10 CHAR)  빈칸 0, 고유값 4  (앞자리 0 → 문자열 유지)
  기본키 후보: cust_no
```
```sql
CREATE TABLE TB_CUSTOMER (
    cust_no VARCHAR2(10 CHAR) NOT NULL,
    zip_code VARCHAR2(10 CHAR) NOT NULL,
    join_date DATE NOT NULL,
    total_amount NUMBER(10) NOT NULL,
    point_rate NUMBER(5,2) NOT NULL,
    memo VARCHAR2(18 CHAR),
    PRIMARY KEY (cust_no)
);
COMMENT ON COLUMN TB_CUSTOMER.cust_no IS '고객번호';
```
(일부 열 생략)

## 주의사항
- 지금 들어 있는 값만 보고 추정합니다. 앞으로 더 긴 값·더 큰 숫자가 올 수 있으면 길이를 넉넉히 고치세요(`--slack`).
- 운영 DB에 바로 실행하지 말고, DBA 검토·명명 규칙(테이블스페이스, 인덱스 등)을 거쳐 쓰세요.
- 샘플 데이터는 가짜입니다.
