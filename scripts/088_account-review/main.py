"""시스템 사용자 계정 목록을 인사 명단과 맞춰 '정리해야 할 계정'을 찾는 스크립트(접근권한 정기 점검).

생각의 흐름:
  1) 계정 목록(시스템에서 내보낸 CSV)과 인사 명단(사번, 이름, 상태, 퇴사일)을 읽습니다.
  2) 사번으로 짝을 지어 아래를 찾습니다.
     - 퇴사자 잔존 계정 : 인사 상태가 퇴사인데 계정이 '사용' (퇴사일 뒤에 접속했으면 따로 표시)
     - 휴직자 활성 계정 : 휴직 중인데 계정이 '사용'
     - 명단에 없는 계정 : 사번이 비었거나 인사 명단에 없음(공용·테스트·외주 계정 후보)
     - 장기 미접속     : 마지막 접속이 N일(기본 90일) 넘음
     - 관리자 권한 과다 : 관리자 역할인데 허용 목록(--admins)에 없음
  3) 계정마다 걸린 항목을 모두 적고, 조치 제안(잠금/확인/권한 회수)을 붙입니다.
  비밀번호나 개인정보는 읽지도 쓰지도 않습니다.
"""
import argparse
import csv
from datetime import date, datetime
from pathlib import Path


def read(path):
    with path.open(newline="", encoding="utf-8-sig") as fp:
        return list(csv.DictReader(fp))


def main():
    p = argparse.ArgumentParser(description="계정·권한 정기 점검")
    p.add_argument("accounts", type=Path, help="계정 CSV(계정ID,사번,역할,상태,마지막접속)")
    p.add_argument("hr", type=Path, help="인사 CSV(사번,이름,재직상태,퇴사일)")
    p.add_argument("--today", default=date.today().isoformat(), help="기준일 YYYY-MM-DD")
    p.add_argument("--idle-days", type=int, default=90, help="장기 미접속 기준(일)")
    p.add_argument("--admin-roles", default="ADMIN,관리자", help="관리자 역할 이름(쉼표)")
    p.add_argument("--admins", default="", help="관리자 허용 계정ID(쉼표)")
    p.add_argument("-o", "--output", type=Path, default=Path("output/account_review.csv"))
    a = p.parse_args()

    today = date.fromisoformat(a.today)
    hr = {r["사번"].strip(): r for r in read(a.hr)}
    admin_roles = {x.strip().upper() for x in a.admin_roles.split(",") if x.strip()}
    allowed = {x.strip() for x in a.admins.split(",") if x.strip()}
    out, counts = [], {}
    for acc in read(a.accounts):
        active = acc["상태"].strip() in ("사용", "ACTIVE", "Y")
        emp = hr.get(acc.get("사번", "").strip())
        issues, action = [], ""
        if emp is None:
            issues.append("명단에 없는 계정")
            action = "담당자 확인"
        else:
            st = emp["재직상태"].strip()
            if st == "퇴사" and active:
                issues.append(f"퇴사자 잔존(퇴사일 {emp.get('퇴사일', '')})")
                action = "즉시 잠금"
                last_s = (acc.get("마지막접속") or "")[:10]
                if last_s and emp.get("퇴사일") and last_s > emp["퇴사일"].strip():
                    issues.append("퇴사일 이후 접속")  # 보안 담당자에게 바로 알릴 사항
            elif st == "휴직" and active:
                issues.append("휴직자 활성")
                action = "잠금 검토"
        last = (acc.get("마지막접속") or "").strip()
        if active:
            if not last:
                issues.append("접속 기록 없음")
            else:
                idle = (today - datetime.strptime(last[:10], "%Y-%m-%d").date()).days
                if idle > a.idle_days:
                    issues.append(f"장기 미접속({idle}일)")
                    action = action or "잠금 검토"
        if acc.get("역할", "").strip().upper() in admin_roles and acc["계정ID"].strip() not in allowed:
            issues.append("관리자 권한 허용목록 밖")
            action = action or "권한 회수 검토"
        for i in issues:
            k = i.split("(")[0]
            counts[k] = counts.get(k, 0) + 1
        out.append({"계정ID": acc["계정ID"], "사번": acc.get("사번", ""), "이름": emp["이름"] if emp else "",
                    "역할": acc.get("역할", ""), "계정상태": acc["상태"], "마지막접속": last,
                    "점검결과": " / ".join(issues) or "정상", "조치제안": action})
    out.sort(key=lambda x: (x["점검결과"] == "정상", x["조치제안"] != "즉시 잠금"))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.DictWriter(fp, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    bad = sum(1 for x in out if x["점검결과"] != "정상")
    print(f"계정 {len(out)}개 중 조치 필요 {bad}개 (기준일 {today}) → {a.output}")
    for k, v in counts.items():
        print(f"  - {k}: {v}개")


if __name__ == "__main__":
    main()
