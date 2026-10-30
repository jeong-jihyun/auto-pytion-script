# 152 오래된 lock·pid 파일 점검

## 무엇을 하나요?
배치가 비정상 종료되며 남긴 `*.lock`, `*.pid` 파일을 찾습니다. **너무 오래된 파일**과 **안에 적힌 PID의 프로세스가 이미 없는 파일**을 '의심'으로 표시해 점검표(CSV)를 만듭니다.

## 어떤 업무에 쓰나요?
- "어제 배치가 죽어서 오늘 배치가 '이미 실행 중'이라며 안 돌았다" 사고 예방
- 아침 배치 점검 체크리스트의 한 항목

## 설치
파이썬 3.8 이상. 추가 설치 없음. (리눅스는 /proc, 그 밖의 OS는 os.kill(pid,0)로 확인)

## 실행 예시
```bash
python make_sample.py                          # 샘플 lock 폴더 만들기
python main.py sample/locks                    # 보고만 (기본)
python main.py /app/batch/lock --max-age-min 120
python main.py /app/batch/lock --apply         # 의심 파일을 격리 폴더로 이동
```

## 출력 예시
```
검사 4개 / 의심 2개 → lock_check.out.csv
  [의심] daily_settle.lock: 오래됨(360분), PID 999999 없음 → 미리보기(--apply 시 격리)
  [의심] this_shell.pid: PID 12345 없음 → 미리보기(--apply 시 격리)
```

## 주의사항
- **삭제하지 않습니다.** `--apply` 때도 격리 폴더로 옮기기만 하니, 잘못 옮겼으면 다시 가져다 놓으면 됩니다.
- PID 확인은 **이 스크립트를 돌리는 서버 기준**입니다. 다른 서버의 배치가 공유 폴더에 만든 lock은 PID 판정이 틀릴 수 있으니 `--max-age-min` 판정만 참고하세요.
- 실행 중인 배치의 lock을 옮기면 중복 실행이 생길 수 있습니다. 반드시 담당자 확인 후 `--apply` 하세요.
