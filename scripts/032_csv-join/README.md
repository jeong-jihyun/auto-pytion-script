# 032 CSV 결합 (VLOOKUP 같은 일)

## 무엇을 하나요?
CSV 두 개를 **같은 값을 가진 열(키)** 로 이어 붙입니다. 엑셀의 VLOOKUP, DB의 JOIN과 같은 일입니다.

## 어떤 업무에 쓰나요?
주문 목록에 고객 등급 붙이기, 거래 내역에 종목명 붙이기, 사원번호로 부서명 붙이기 등.

## 설치
파이썬 3.8 이상. 따로 설치할 것 없음.

## 실행 예시
```
python3 main.py sample/orders.csv sample/customers.csv --key 고객코드 -o output/joined.csv
python3 main.py sample/orders.csv sample/customers.csv --key 고객코드 --how inner
```

## 입력 / 출력 예시
주문(A003은 고객코드 C09 → 고객표에 없음) → `--how left` 면 A003의 고객명·등급이 빈칸, `--how inner` 면 A003 줄이 빠집니다.

## 주의사항
- 키 값 앞뒤 공백은 무시하지만, 대소문자는 구분합니다.
- 오른쪽 표에 같은 키가 여러 줄이면 첫 줄만 쓰고 경고합니다.
- 입력 파일은 바꾸지 않습니다.
