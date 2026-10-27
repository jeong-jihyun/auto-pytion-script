-- 2026-10-27 정산 테이블 운영 반영 (가짜 예시)
-- 주석 속 DELETE FROM settle; 는 검사하지 않습니다

/* 1. 수수료율 변경 */
UPDATE fee_rate
   SET rate = 0.015
 WHERE grade = 'VIP';

/* 2. 실수: 조건이 빠진 수정 */
UPDATE account
   SET status = 'DORMANT';

DELETE FROM settle_tmp WHERE 1=1;

DELETE FROM settle_log;

INSERT INTO fee_hist VALUES (1, 'VIP', 0.015, '변경; DROP 아님');

INSERT INTO fee_hist (id, grade, rate, memo) VALUES (2, 'GOLD', 0.02, 'O''Reilly');

TRUNCATE TABLE batch_err;

ALTER TABLE customer DROP COLUMN old_phone;

GRANT SELECT ON settle TO report_user;

SELECT * FROM fee_rate WHERE grade = 'VIP';
