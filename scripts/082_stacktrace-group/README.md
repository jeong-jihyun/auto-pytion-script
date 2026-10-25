# 082 스택트레이스(예외) 묶음 집계

## 무엇을 하나요?
서버·배치 로그에 섞인 자바/파이썬 예외(여러 줄짜리 스택트레이스)를 찾아, **예외 종류 + 우리 코드의 발생 위치** 가 같은 것끼리 묶고 횟수·처음/마지막 시각을 세어 줍니다. `Caused by:`(근본 원인)도 따로 적습니다.

## 어떤 업무에 쓰나요?
- 장애·배치 실패 후 "오류가 몇 종류였고, 어디서 몇 번 났는지" 보고서 만들기
- 같은 NullPointerException이 수백 번 찍혀도 한 줄로 요약

## 설치
파이썬 3.8 이상. 설치할 것 없음.

## 실행 예시
```
python3 main.py sample/app.log --package com.mycorp -o output/exceptions.csv
python3 main.py logs/*.log --package app/       # 파이썬 프로젝트라면 경로 일부
```

## 입력 / 출력 예시
- 입력: 일반 텍스트 로그. 줄 앞에 `2026-10-25 09:00:05` 형식 시각이 있으면 발생 시각으로 씁니다.
- 출력 CSV 열: `순위, 예외, 근본원인(Caused by), 발생위치, 횟수, 처음, 마지막, 대표메시지, 파일`

샘플 결과: 예외 4건 → 묶음 3개 (NullPointerException @ OrderService.normalize 2회, DataIntegrityViolationException(원인 SQLIntegrityConstraintViolationException) 1회, ZeroDivisionError @ app/settle.py:12 1회)

## 주의사항
- `--package`를 주면 프레임워크 코드가 아닌 **우리 코드 첫 위치** 로 묶어 원인 찾기가 쉬워집니다.
- 로그 형식이 특이하면(한 줄에 스택트레이스를 이어 붙인 JSON 로그 등) 인식하지 못할 수 있습니다.
- 대표메시지에 고객 정보가 찍혀 있을 수 있으니 결과를 공유할 때 확인하세요. 샘플은 가짜 데이터입니다.
