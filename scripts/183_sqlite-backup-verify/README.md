# 183 SQLite 안전 백업 + 무결성 검사

## 무엇을 하나요?
SQLite 데이터베이스 파일(`.db`, `.sqlite`)을 **사용 중이어도 안전하게** 백업하고, 백업본이 멀쩡한지 두 가지로 확인합니다.
1. `PRAGMA integrity_check` — 파일 구조가 깨지지 않았는지
2. 테이블별 행 수 — 원본과 백업이 같은지

검사 결과는 CSV로 남아서 점검 기록으로 쓸 수 있습니다.

## 어떤 업무에 쓰나요?
- 사내 소규모 도구(접수·재고·수집 로그)의 SQLite 파일 매일 백업
- 이관·패치 전에 "백업이 정말 열리는지" 확인
- 백업 점검 결과를 감사·점검 증적으로 보관

## 생각의 흐름
- 프로그램이 쓰는 중에 파일을 그냥 복사하면 반쯤 쓰인 상태가 복사될 수 있습니다. 파이썬 `sqlite3` 의 `backup()` 은 **한 시점의 일관된 사본**을 만들어 줍니다.
- 원본은 **읽기 전용**으로 열어 실수로도 바꾸지 않습니다.
- 백업 파일 이름에 날짜시간을 붙여 **덮어쓰지 않습니다**.

## 설치
파이썬 3.8 이상. 추가 설치 없음(`sqlite3` 는 파이썬에 들어 있음).

## 실행 예시
```bash
python main.py sample/sample.db --check-only          # 원본만 검사
python main.py sample/sample.db                       # 백업 + 검사 (backup_out/ 에 저장)
python main.py D:/tools/inventory.db --out-dir E:/backup/inventory
```
끝날 때 정상이면 종료 코드 0, 문제가 있으면 1을 돌려줍니다. 윈도우 작업 스케줄러·cron 에서 실패 알림 조건으로 쓸 수 있습니다.

## 입력 예시
`sample/sample.db` 는 `sample/create_sample.sql`(가짜 고객 3명, 접수 4건)로 만든 연습용 파일입니다. 다시 만들고 싶으면:
```bash
python -c "import sqlite3; c=sqlite3.connect('sample/sample.db'); c.executescript(open('sample/create_sample.sql',encoding='utf-8').read()); c.commit()"
```

## 출력 예시
```
원본: sample/sample.db
  무결성 검사: ok
  customers: 3행
  tickets: 4행
백업: backup_out/sample_20261113_045045.db (12,288 bytes)
  무결성 검사: ok
  customers: 원본 3 / 백업 3 → 예
  tickets: 원본 4 / 백업 4 → 예
결과: 정상 (기록: backup_out/verify_20261113_045045.csv)
```

## 주의사항
- 오래된 백업을 지우는 기능은 일부러 넣지 않았습니다. 보관 정책은 190번(GFS 백업 보관 정리)을 함께 쓰세요.
- 행 수 비교는 백업 **직후** 기준입니다. 백업과 비교 사이에 원본에 새 행이 들어오면 다를 수 있는데, 이 스크립트는 백업 전에 센 원본 행 수와 비교하므로 사용 중인 DB에서는 "확인 필요"가 나올 수 있습니다. 이때는 한가한 시간에 다시 돌려 보세요.
- SQLite 가 아닌 파일을 주면 "SQLite 파일로 열 수 없습니다"로 멈춥니다.
- 시각은 스크립트를 돌린 컴퓨터의 시계 기준입니다.
