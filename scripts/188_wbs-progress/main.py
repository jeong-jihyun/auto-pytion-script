"""WBS(작업분류) CSV로 가중치를 반영한 프로젝트 공정률(계획 대비 실적)을 계산하는 스크립트.

생각의 흐름:
  1) SI·ERP 프로젝트 주간 보고에는 "계획 공정률 62%, 실적 58%" 같은 숫자가 들어갑니다.
  2) 실제 진척은 맨 아래 작업(리프)에만 적습니다. 위 단계(1, 1.2 ...)는 아래 작업의 가중 평균으로 계산합니다.
       상위 진척 = Σ(하위 가중치 × 하위 진척) ÷ Σ(하위 가중치)
  3) WBS 코드의 점(.)으로 부모를 찾습니다. 1.2.3 의 부모는 1.2, 1.2 의 부모는 1 입니다.
  4) 상위 항목에 적힌 진척 값은 무시하고 다시 계산합니다(손으로 적은 값과 어긋나는 일이 많기 때문).
     대신 상위 항목의 가중치는 '형제들 사이의 비중'으로 씁니다.
  5) 실적이 계획보다 기준(기본 5%p) 이상 뒤처진 리프 작업을 '지연'으로 뽑습니다.
"""
import argparse
import os
import csv
import sys


def to_num(v, name, code):
    v = (v or "").strip().rstrip("%")
    if v == "":
        return None
    try:
        return float(v)
    except ValueError:
        sys.exit(f"[오류] {code} 의 {name} '{v}' 가 숫자가 아닙니다.")


def main():
    ap = argparse.ArgumentParser(description="WBS 가중 공정률 계산")
    ap.add_argument("input", help="WBS CSV (WBS,작업명,가중치,계획%,실적%,담당)")
    ap.add_argument("--late-gap", type=float, default=5.0, help="계획-실적 차이가 이 값 이상이면 지연 (기본 5%%p)")
    ap.add_argument("--output", default="output/wbs_progress.md")
    args = ap.parse_args()

    with open(args.input, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    items, order = {}, []
    for r in rows:
        code = r["WBS"].strip()
        if not code:
            continue
        if code in items:
            sys.exit(f"[오류] WBS 코드 {code} 가 두 번 나옵니다.")
        items[code] = {
            "code": code, "name": r.get("작업명", "").strip(), "owner": r.get("담당", "").strip(),
            "w": to_num(r.get("가중치"), "가중치", code) or 0.0,
            "plan": to_num(r.get("계획%"), "계획%", code), "act": to_num(r.get("실적%"), "실적%", code),
            "kids": [],
        }
        order.append(code)

    roots, warn = [], []
    for code in order:
        parent = code.rsplit(".", 1)[0] if "." in code else None
        if parent and parent in items:
            items[parent]["kids"].append(code)
        else:
            if parent:
                warn.append(f"{code}: 부모 {parent} 가 없어 맨 위 항목으로 처리")
            roots.append(code)

    def calc(code):
        it = items[code]
        if not it["kids"]:
            if it["plan"] is None or it["act"] is None:
                warn.append(f"{code} {it['name']}: 계획%/실적% 가 비어 있어 0 으로 계산")
            it["plan"] = it["plan"] or 0.0
            it["act"] = it["act"] or 0.0
            return
        for k in it["kids"]:
            calc(k)
        total_w = sum(items[k]["w"] for k in it["kids"])
        if total_w == 0:
            warn.append(f"{code}: 하위 가중치 합이 0 이라 단순 평균으로 계산")
            n = len(it["kids"])
            it["plan"] = sum(items[k]["plan"] for k in it["kids"]) / n
            it["act"] = sum(items[k]["act"] for k in it["kids"]) / n
        else:
            it["plan"] = sum(items[k]["w"] * items[k]["plan"] for k in it["kids"]) / total_w
            it["act"] = sum(items[k]["w"] * items[k]["act"] for k in it["kids"]) / total_w

    for r in roots:
        calc(r)
    tw = sum(items[r]["w"] for r in roots) or len(roots)
    if sum(items[r]["w"] for r in roots):
        total_plan = sum(items[r]["w"] * items[r]["plan"] for r in roots) / tw
        total_act = sum(items[r]["w"] * items[r]["act"] for r in roots) / tw
    else:
        total_plan = sum(items[r]["plan"] for r in roots) / tw
        total_act = sum(items[r]["act"] for r in roots) / tw

    lines = ["| WBS | 작업명 | 가중치 | 계획% | 실적% | 차이 | 담당 |", "|---|---|---:|---:|---:|---:|---|"]
    late = []
    for code in order:
        it = items[code]
        depth = code.count(".")
        gap = it["act"] - it["plan"]
        name = ("　" * depth) + (f"**{it['name']}**" if it["kids"] else it["name"])
        lines.append(f"| {code} | {name} | {it['w']:g} | {it['plan']:.1f} | {it['act']:.1f} | {gap:+.1f} | {it['owner']} |")
        if not it["kids"] and -gap >= args.late_gap:
            late.append(it)

    late.sort(key=lambda x: x["act"] - x["plan"])
    out = ["# 공정률 보고", "",
           f"- 전체 계획 공정률: **{total_plan:.1f}%**",
           f"- 전체 실적 공정률: **{total_act:.1f}%**",
           f"- 차이: **{total_act - total_plan:+.1f}%p** ({'앞섬' if total_act >= total_plan else '뒤처짐'})", "",
           "## WBS 별", *lines, "", f"## 지연 작업 (계획보다 {args.late_gap:g}%p 이상 뒤처짐)"]
    out += [f"- {x['code']} {x['name']} ({x['owner']}): 계획 {x['plan']:.0f}% / 실적 {x['act']:.0f}%" for x in late] or ["- 없음"]
    if warn:
        out += ["", "## 확인할 점", *[f"- {w}" for w in warn]]

    d = os.path.dirname(args.output)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print("\n".join(out))
    print("-" * 40)
    print(f"저장: {args.output}")


if __name__ == "__main__":
    main()
