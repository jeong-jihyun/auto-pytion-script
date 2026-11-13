-- 연습용 가짜 데이터: 작은 접수 관리 DB
CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT, branch TEXT);
CREATE TABLE tickets (id INTEGER PRIMARY KEY, customer_id INTEGER, title TEXT, status TEXT, created TEXT);
INSERT INTO customers VALUES (1,'가나상사','본점'),(2,'다라물산','강남'),(3,'마바유통','부산');
INSERT INTO tickets VALUES
 (1,1,'정산 파일 누락 문의','완료','2026-11-10'),
 (2,2,'수수료 계산 확인','진행','2026-11-11'),
 (3,3,'월말 리포트 요청','접수','2026-11-12'),
 (4,1,'계좌 등록 변경','접수','2026-11-12');
