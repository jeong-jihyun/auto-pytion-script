"""로그 파일의 줄마다 해시를 사슬처럼 이어 기록해 두고, 나중에 로그가 고쳐지거나 지워졌는지 확인하는 스크립트.

생각의 흐름:
  1) 감사·보안 점검에서 "이 접근 로그가 중간에 고쳐지지 않았다는 걸 어떻게 보장하나요?"라는 질문을 받습니다.
  2) 파일 전체 해시 하나만 두면 '바뀌었다'는 것만 알고 '어디가' 바뀌었는지는 모릅니다.
  3) 그래서 줄마다 해시를 이어 붙입니다(해시 체인).
       h0 = SHA-256("시작값")
       h1 = SHA-256(h0 + 1번째 줄)
       h2 = SHA-256(h1 + 2번째 줄) ...
     중간 한 줄이 바뀌면 그 줄부터 뒤의 해시가 모두 달라지므로, '처음 달라진 줄'이 고쳐진 곳입니다.
  4) 로그는 계속 뒤에 쌓이므로, 기록 이후 '뒤에 추가된 줄'은 위변조가 아니라 정상으로 따로 알려 줍니다.
     반대로 기록보다 줄 수가 줄었으면 '끝부분 삭제'입니다.
  5) 체인 파일(CSV)은 로그와 다른 곳(다른 서버·읽기 전용 저장소)에 보관해야 의미가 있습니다.
     같은 사람이 로그와 체인을 함께 고칠 수 있으면 위변조를 막지 못합니다.
"""
import argparse
import csv
import hashlib
import os
import sys

SEED = "auto-pytion-script/log-hash-chain/v1"


def chain_hashes(path, seed):
    prev = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    with open(path, "rb") as f:
        for no, raw in enumerate(f, start=1):
            line = raw.rstrip(b"\r\n")
            prev = hashlib.sha256(prev.encode("ascii") + line).hexdigest()
            yield no, prev


def cmd_make(args):
    out = args.chain or args.log + ".chain.csv"
    if os.path.exists(out) and not args.overwrite:
        sys.exit(f"[중단] 체인 파일이 이미 있습니다: {out} (다시 만들려면 --overwrite)")
    n, last = 0, ""
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["줄번호", "누적해시"])
        for n, h in chain_hashes(args.log, args.seed):
            w.writerow([n, h])
            last = h
    print(f"기록 완료: {args.log} → {out}")
    print(f"  줄 수 {n}, 마지막 해시 {last[:16]}...")
    print("  ※ 체인 파일은 로그와 다른 곳(읽기 전용 저장소 등)에 보관하세요.")


def cmd_verify(args):
    chain_path = args.chain or args.log + ".chain.csv"
    with open(chain_path, encoding="utf-8", newline="") as f:
        saved = [row[1] for row in list(csv.reader(f))[1:]]
    current = [h for _, h in chain_hashes(args.log, args.seed)]

    print(f"검사: {args.log} (기록 {len(saved)}줄 / 현재 {len(current)}줄)")
    for i, (a, b) in enumerate(zip(saved, current), start=1):
        if a != b:
            print(f"[위변조 의심] {i}번째 줄부터 내용이 기록과 다릅니다(그 줄이 고쳐졌거나, 그 앞에 줄이 끼워지거나 빠졌습니다).")
            with open(args.log, "rb") as lf:
                for no, raw in enumerate(lf, start=1):
                    if no == i:
                        print(f"  현재 {i}번째 줄: {raw.rstrip(chr(10).encode()).decode('utf-8', 'replace')[:120]}")
                        break
            sys.exit(2)
    if len(current) < len(saved):
        print(f"[위변조 의심] 끝부분 {len(saved) - len(current)}줄이 사라졌습니다({len(current) + 1}번째 줄부터).")
        sys.exit(2)
    if len(current) > len(saved):
        print(f"[정상] 기록한 {len(saved)}줄은 그대로이고, 그 뒤에 {len(current) - len(saved)}줄이 새로 쌓였습니다.")
        print("       새 줄까지 보호하려면 make --overwrite 로 체인을 다시 기록하세요.")
    else:
        print("[정상] 기록과 완전히 같습니다.")


def main():
    ap = argparse.ArgumentParser(description="로그 해시 체인 기록·검증")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn, helptext in (("make", cmd_make, "체인 기록하기"), ("verify", cmd_verify, "기록과 비교하기")):
        p = sub.add_parser(name, help=helptext)
        p.add_argument("log", help="로그 파일")
        p.add_argument("--chain", help="체인 CSV 경로 (기본: 로그파일.chain.csv)")
        p.add_argument("--seed", default=SEED, help="시작값(기록·검증 때 같아야 함)")
        if name == "make":
            p.add_argument("--overwrite", action="store_true", help="기존 체인 파일 덮어쓰기")
        p.set_defaults(func=fn)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
