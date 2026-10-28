-- 일 마감 배치 v2
SELECT acct_no, SUM(amt) AS total,   COUNT(*) AS cnt
  FROM trade_daily
 WHERE trade_dt = :base_dt
   AND cancel_yn = 'N'
 GROUP BY acct_no;

UPDATE acct_balance SET close_yn = 'Y'
 WHERE base_dt  =  :base_dt;
