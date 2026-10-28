# 140 JSON Lines 구조화 로그 필터·집계

## 무엇을 하나요?
한 줄에 JSON 하나씩 쌓이는 로그(`.jsonl`, `.log`, 압축된 `.gz`)를 읽어
- `--where` 조건으로 거르고(여러 개면 모두 만족)
- `--by` 필드 조합별 건수·비율을 세고
- `--value` 숫자 필드의 평균·p95·최대를 계산합니다.
- 조건에 맞는 원본 줄만 따로 저장(`--export`)할 수도 있습니다.

조건 쓰는 법: `=`(같음), `!=`(다름), `>=`·`<=`(숫자 비교), `~`(포함). 안쪽 필드는 점으로: `http.status>=500`

## 어떤 업무에 쓰나요?
- 장애 때 'ERROR가 어느 서비스·어느 코드에서 몇 건, 응답시간은?'을 바로 확인
- 정산·주문 서비스의 오류 코드별 일일 집계(텍스트 로그는 004, 접속 로그 응답시간은 054 참고)

## 설치
파이썬 3.8 이상. 설치할 것 없음.

## 실행 예시
```
python3 main.py sample/app.jsonl --by service,level --value latency_ms -o output/jsonl_summary.csv
python3 main.py sample/app.jsonl --where level=ERROR --where "http.status>=500" --by code --value latency_ms --export output/errors.jsonl
python3 main.py logs/app-2026-10-27.jsonl.gz --where "msg~지연" --by service
```
(`>=`, `~` 가 들어간 조건은 따옴표로 감싸세요)

## 출력 예시
```
읽은 줄 9개, 조건 맞음 2개, JSON 깨짐 1개 (예: app.jsonl:7)
조건: level=ERROR 그리고 http.status>=500
code | 건수 | 비율(%) | latency_ms_평균 | latency_ms_p95 | latency_ms_최대
DB_TIMEOUT | 2 | 100.0 | 3175.0 | 3300 | 3300
```
필드가 없는 줄은 `(없음)` 으로 묶입니다. 숫자가 아닌 값은 통계에서 빠집니다.

## 주의사항
- JSON이 깨진 줄은 건너뛰고 앞쪽 5개 위치만 알려 줍니다.
- 로그에 개인정보가 있으면 `--export` 파일 관리에 주의하세요.
- p95는 가장 가까운 순위 값(보간 없음)입니다.
- 샘플 로그는 가짜입니다.
