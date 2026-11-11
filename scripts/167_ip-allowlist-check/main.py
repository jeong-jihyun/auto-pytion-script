"""접속 로그의 IP가 허용된 IP 대역(사내망, 협력사 VPN 등) 안에 있는지 확인해, 허용 밖 접속을 찾는 스크립트.

생각의 흐름:
  1) 관리자 페이지·DB·배치 서버는 정해진 대역에서만 접속해야 합니다. 방화벽이 막더라도
     설정 실수가 있을 수 있어, 로그를 보고 '정말 허용 대역에서만 왔는지' 정기 점검을 합니다.
  2) 허용 목록은 '대역  이름' 한 줄씩 적은 텍스트로 받습니다(예: 10.10.0.0/16 본사망).
     파이썬 표준 ipaddress 모듈이 IPv4·IPv6 대역 계산을 정확히 해 줍니다.
  3) 로그 형식이 제각각이라 두 가지를 받습니다.
       - 텍스트 로그: 줄에서 처음 나오는 IP 모양 글자를 씀 (아파치/엔진엑스 접속 로그 등)
       - CSV: --ip-column 으로 IP 열을 지정
  4) 같은 IP가 수천 번 나와도 보고서는 IP별로 한 줄(횟수, 처음·마지막 줄)로 묶어 보기 쉽게 합니다.
  5) 사설망 IP인데 허용 목록에 없는 것과, 공인 IP인 것은 위험도가 다르므로 '구분' 열로 나눠 표시합니다.
  6) 허용 밖 접속이 하나라도 있으면 종료코드 1을 돌려, 스케줄러에서 알림을 걸 수 있게 했습니다.
"""
import argparse
import csv
import ipaddress
import re
import sys
from collections import OrderedDict

# 줄을 이 글자들로 잘라 조각마다 IP인지 확인합니다(정규식으로 IPv6를 다 맞추기는 어려워서)
SPLIT_RE = re.compile(r"[\s\[\]\"',;=()<>]+")
# 사설망(회사 내부망에 쓰는 대역). 표준 모듈의 is_private 는 문서용·특수 대역까지 포함해서 직접 적습니다.
PRIVATE = [ipaddress.ip_network(n) for n in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "fc00::/7")]


def load_allowlist(path):
    nets = []
    with open(path, encoding="utf-8-sig") as f:
        for no, line in enumerate(f, 1):
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            parts = line.split(None, 1)
            try:
                net = ipaddress.ip_network(parts[0], strict=False)
            except ValueError:
                sys.exit(f"허용 목록 {no}번째 줄의 대역이 이상합니다: {parts[0]}")
            nets.append((net, parts[1].strip() if len(parts) > 1 else str(net)))
    return nets


def find_ip(text):
    for tok in SPLIT_RE.split(text):
        if not tok or ("." not in tok and ":" not in tok):
            continue
        try:
            return ipaddress.ip_address(tok)
        except ValueError:
            continue
    return None


def iter_ips(path, ip_column, encoding):
    """(줄번호, ip객체 또는 None, 원문) 을 차례로 돌려줍니다."""
    with open(path, newline="", encoding=encoding, errors="replace") as f:
        if ip_column:
            for no, row in enumerate(csv.DictReader(f), 2):
                raw = (row.get(ip_column) or "").strip()
                try:
                    yield no, ipaddress.ip_address(raw), raw
                except ValueError:
                    yield no, None, raw
        else:
            for no, line in enumerate(f, 1):
                if line.strip():
                    yield no, find_ip(line), line.strip()[:80]


def main():
    p = argparse.ArgumentParser(description="접속 IP 허용 대역 점검")
    p.add_argument("log", help="접속 로그(텍스트) 또는 CSV")
    p.add_argument("-a", "--allowlist", required=True, help="허용 대역 목록 파일('대역 이름' 한 줄씩)")
    p.add_argument("--ip-column", help="CSV일 때 IP 열 이름")
    p.add_argument("-o", "--output", default="ip_check.out.csv")
    p.add_argument("--show-allowed", action="store_true", help="허용된 IP도 결과에 포함")
    p.add_argument("--encoding", default="utf-8-sig")
    a = p.parse_args()

    nets = load_allowlist(a.allowlist)
    stats = OrderedDict()
    bad_lines = 0
    for no, ip, raw in iter_ips(a.log, a.ip_column, a.encoding):
        if ip is None:
            bad_lines += 1
            continue
        if ip.version == 6 and ip.ipv4_mapped:  # ::ffff:10.0.0.1 → 10.0.0.1
            ip = ip.ipv4_mapped
        s = stats.get(ip)
        if s is None:
            label = next((name for net, name in nets if ip.version == net.version and ip in net), "")
            if label:
                kind = "허용"
            elif ip.is_loopback:
                kind = "루프백(확인)"
            elif any(ip.version == n.version and ip in n for n in PRIVATE):
                kind = "사설망-목록에 없음"
            else:
                kind = "공인IP-허용 밖"
            s = stats[ip] = {"구분": kind, "허용대역": label, "횟수": 0, "처음줄": no, "마지막줄": no}
        s["횟수"] += 1
        s["마지막줄"] = no

    rows = []
    for ip, s in stats.items():
        if s["구분"] == "허용" and not a.show_allowed:
            continue
        rows.append({"IP": str(ip), **s})
    order = {"공인IP-허용 밖": 0, "사설망-목록에 없음": 1, "루프백(확인)": 2, "허용": 3}
    rows.sort(key=lambda r: (order[r["구분"]], -r["횟수"]))
    with open(a.output, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["IP", "구분", "허용대역", "횟수", "처음줄", "마지막줄"])
        w.writeheader()
        w.writerows(rows)

    total = sum(s["횟수"] for s in stats.values())
    outside = [r for r in rows if r["구분"] != "허용"]
    print(f"IP {len(stats)}개 / 접속 {total}줄 점검 (IP 못 찾은 줄 {bad_lines}) → {a.output}")
    if outside:
        print(f"⚠ 허용 밖 IP {len(outside)}개")
        for r in outside[:10]:
            print(f"  {r['IP']:<18} {r['구분']:<14} {r['횟수']}회 (줄 {r['처음줄']}~{r['마지막줄']})")
        sys.exit(1)
    print("모든 접속이 허용 대역 안입니다.")


if __name__ == "__main__":
    main()
