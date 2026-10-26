"""XML 파일에서 반복되는 레코드(예: <거래>)를 찾아 한 줄씩 CSV 표로 펼치는 스크립트.

생각의 흐름:
  1) 은행·관공서·타 시스템 연계 파일은 XML로 오는 경우가 많은데, 엑셀로 보려면 표가 필요합니다.
  2) '한 건'에 해당하는 태그 이름(--record)을 알려 주면 그 태그를 모두 찾습니다.
     모르면 --record 없이 실행해 '가장 많이 반복되는 태그' 후보를 먼저 봅니다.
  3) 레코드 안의 하위 태그는 '부모/자식' 경로를 열 이름으로, 속성은 '@속성' 으로 만듭니다.
     같은 이름이 여러 번 나오면 '항목[2]'처럼 번호를 붙여 값이 사라지지 않게 합니다.
  4) 레코드마다 열이 조금씩 달라도 전체 열을 모아 빈칸으로 맞춰 CSV를 만듭니다.
  5) 네임스페이스({http://...}태그)는 열 이름이 지저분해지므로 떼어 냅니다.
  * 보안: 표준 ElementTree는 외부 엔티티를 불러오지 않습니다. 그래도 출처를 모르는 큰 XML은 조심하세요.
"""
import argparse
import csv
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path


def local(tag):
    return tag.split("}", 1)[-1]


def flatten(elem, prefix, out):
    """elem 아래 값을 {열이름: 값} 으로 모읍니다."""
    for k, v in elem.attrib.items():
        out[f"{prefix}@{local(k)}" if prefix else f"@{local(k)}"] = v
    seen = Counter()
    for child in elem:
        name = local(child.tag)
        seen[name] += 1
        key = f"{prefix}{name}" + (f"[{seen[name]}]" if seen[name] > 1 else "")
        if len(child) or child.attrib:
            flatten(child, key + "/", out)
            if (child.text or "").strip():
                out[key] = child.text.strip()
        else:
            out[key] = (child.text or "").strip()


def main():
    p = argparse.ArgumentParser(description="XML 레코드를 CSV로 펼치기")
    p.add_argument("xml", type=Path, help="XML 파일")
    p.add_argument("--record", help="한 건에 해당하는 태그 이름(모르면 비워 두고 실행)")
    p.add_argument("-o", "--output", type=Path, default=Path("output/records.csv"))
    a = p.parse_args()

    root = ET.parse(a.xml).getroot()
    if not a.record:
        c = Counter(local(e.tag) for e in root.iter())
        print("반복 태그 후보(많은 순). 이 중 한 건에 해당하는 태그를 --record 로 주세요:")
        for tag, n in c.most_common(8):
            print(f"  {tag}: {n}개")
        return

    records = []
    for e in root.iter():
        if local(e.tag) == a.record:
            row = {}
            flatten(e, "", row)
            records.append(row)
    cols = []
    for r in records:
        for k in r:
            if k not in cols:
                cols.append(k)  # 처음 나온 순서를 유지

    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("w", newline="", encoding="utf-8-sig") as fp:
        w = csv.DictWriter(fp, fieldnames=cols)
        w.writeheader()
        w.writerows(records)
    print(f"<{a.record}> {len(records)}건, 열 {len(cols)}개 → {a.output}")
    print("열: " + ", ".join(cols))


if __name__ == "__main__":
    main()
