# 038 설정 파일 비교

## 무엇을 하나요?
개발/운영처럼 **두 환경의 설정 파일을 비교**해서 빠진 항목, 값이 다른 항목을 찾아 줍니다. 비밀번호·토큰 같은 값은 화면에 **보여 주지 않습니다.**

## 어떤 업무에 쓰나요?
배포 전 설정 누락 점검, 운영 이관 체크, 서버 간 설정 차이 확인(ERP·배치 환경 점검).

## 설치
파이썬 3.8 이상. 따로 설치할 것 없음.

## 실행 예시
```
python3 main.py sample/dev.json sample/prod.json
python3 main.py a.env b.env --ignore DEBUG
```

## 입력 / 출력 예시
```
[기준에만 있음] app.debug = True
[값 다름] app.timeout: 30 -> 60
[값 다름] db.host: 'dev-db.example.local' -> 'prod-db.example.local'
[값 다름] db.password: (가림) -> (가림)
[비교에만 있음] monitoring.enabled = True
```
차이가 있으면 끝 코드 1, 없으면 0 입니다.

## 주의사항
- `.json` 이 아닌 파일은 `KEY=VALUE` 줄 형식(.env, 간단한 .ini)으로 읽습니다.
- 실제 비밀번호가 든 파일은 저장소에 올리지 마세요. 예시는 가짜 값입니다.
