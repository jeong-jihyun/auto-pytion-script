-- 일 마감 배치 v1
SELECT acct_no, SUM(amt) AS total
  FROM trade_daily
 WHERE trade_dt = :base_dt
 GROUP BY acct_no;

UPDATE acct_balance SET close_yn = 'Y'
 WHERE base_dt = :base_dt;
