# 167 접속 IP 허용 대역 점검

## 무엇을 하나요?
접속 로그(또는 CSV)의 IP가 **허용 대역 목록**(사내망, 협력사 VPN 등) 안에 있는지 확인하고, **허용 밖 IP**를 횟수·처음/마지막 줄과 함께 정리합니다. IPv4·IPv6 모두 됩니다.

## 어떤 업무에 쓰나요?
- 관리자 페이지·DB·배치 서버 접속 IP 정기 점검(보안 점검 증적)
- 방화벽·접근제어 설정 실수 찾기
- VPN 접속 기록에서 허용되지 않은 위치의 접속 찾기

## 설치
파이썬 3.8 이상. 추가 설치 없음.

## 허용 목록 형식 (allowlist.txt)
```
# 대역            이름
10.10.0.0/16       본사망
10.20.5.0/24       협력사VPN
2001:db8:10::/48   본사IPv6
```

## 실행 예시
```bash
python main.py sample/access.log -a sample/allowlist.txt
python main.py sample/vpn_sessions.csv -a sample/allowlist.txt --ip-column 접속IP
python main.py sample/access.log -a sample/allowlist.txt --show-allowed   # 허용 IP도 표에 포함
```

## 출력 예시
```
IP 8개 / 접속 11줄 점검 (IP 못 찾은 줄 1) → ip_check.out.csv
⚠ 허용 밖 IP 3개
  203.0.113.45       공인IP-허용 밖     3회 (줄 4~6)
  172.16.9.8         사설망-목록에 없음  1회 (줄 7~7)
  127.0.0.1          루프백(확인)       1회 (줄 12~12)
```
- `::ffff:10.10.7.7` 같은 IPv4 매핑 주소는 `10.10.7.7` 로 바꿔 판단합니다.
- 허용 밖 IP가 있으면 종료코드 1(스케줄러 알림용), 없으면 0입니다.

## 주의사항
- 로드밸런서·프록시 뒤의 서버 로그는 실제 사용자 IP가 아니라 프록시 IP가 찍힐 수 있습니다. 그럴 땐 X-Forwarded-For 값이 든 열을 `--ip-column` 으로 쓰세요.
- 이 스크립트는 기록을 점검만 하고 차단은 하지 않습니다. 샘플 IP는 문서용 예시 대역입니다.
