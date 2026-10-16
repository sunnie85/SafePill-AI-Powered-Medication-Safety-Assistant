"""
Đánh giá chức năng cảnh báo tương tác thuốc của SafePill so với danh sách chuẩn do con người tra cứu.

Cách dùng:
    python eval_interactions.py --gold data/interaction_gold.csv --out results/interaction_report.md

gold.csv: drug_a, drug_b, expected (yes/no), severity (Cao/Trung bình/Thấp, có thể để trống), source (link/tên nguồn)
  - Cặp 'yes' lấy từ Drugs.com Interaction Checker / Dược thư Quốc gia VN (ghi rõ nguồn từng dòng).
  - Cặp 'no' là cặp thuốc thường dùng chung nhưng KHÔNG có tương tác đáng kể theo nguồn đó.
  - Nên có cả thuốc NGOÀI cơ sở dữ liệu của app để đo "độ phủ".

Cần tách các hàm thuần (không dùng streamlit) sang safepill_core.py:
    INTERACTION_DATABASE, build_symmetric_lookup, INTERACTION_LOOKUP, BRAND_TO_GENERIC,
    _strip_accents, normalize_drug_name, check_interaction (+ các hằng số nguồn mà chúng dùng).
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "code")]  # safepill_core nằm ở gốc repo (hoặc code/)
from safepill_core import check_interaction, normalize_drug_name


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", required=True)
    ap.add_argument("--out", default="results/interaction_report.md")
    a = ap.parse_args()
    df = pd.read_csv(a.gold, dtype=str).fillna("")

    rec = []
    for _, r in df.iterrows():
        in_scope = normalize_drug_name(r["drug_a"])[0] is not None and normalize_drug_name(r["drug_b"])[0] is not None
        hit = check_interaction(r["drug_a"], r["drug_b"])
        expected = r["expected"].strip().lower() == "yes"
        sev_ok = None
        if hit and expected and r.get("severity", "").strip():
            sev_ok = hit["severity"].strip().lower() == r["severity"].strip().lower()
        rec.append({**r.to_dict(), "in_scope": in_scope, "detected": hit is not None,
                    "expected_b": expected, "sev_ok": sev_ok})
    d = pd.DataFrame(rec)

    pos, neg = d[d["expected_b"]], d[~d["expected_b"]]
    tp = int((pos["detected"]).sum())
    fn_in = int((~pos["detected"] & pos["in_scope"]).sum())
    fn_out = int((~pos["in_scope"]).sum())
    fp = int(neg["detected"].sum())
    sev = d["sev_ok"].dropna()

    def pct(k, n):
        return f"{k / n:.1%} ({k}/{n})" if n else "n/a"

    lines = [
        "# Báo cáo đánh giá cảnh báo tương tác thuốc\n",
        "| Chỉ số | Kết quả |", "|---|---|",
        f"| Số cặp chuẩn (có / không tương tác) | {len(pos)} / {len(neg)} |",
        f"| Độ phủ: cặp mà CẢ HAI thuốc có trong CSDL | {pct(int(d['in_scope'].sum()), len(d))} |",
        f"| Recall trong phạm vi CSDL (bắt được / cặp có tương tác & thuốc đã biết) | {pct(tp, tp + fn_in)} |",
        f"| Recall tổng thể (tính cả cặp ngoài CSDL, app im lặng) | {pct(tp, len(pos))} |",
        f"| Bỏ sót do thuốc ngoài CSDL (app KHÔNG cảnh báo) | {fn_out} cặp |",
        f"| Báo nhầm (cặp không tương tác nhưng app cảnh báo) | {pct(fp, len(neg))} |",
        f"| Đúng mức độ nghiêm trọng (trên cặp bắt được có nhãn) | {pct(int(sev.sum()), len(sev)) if len(sev) else 'n/a'} |",
        "\n## Các cặp bị bỏ sót (cần bổ sung CSDL)\n",
    ]
    miss = pos[~pos["detected"]]
    lines += [f"- {r.drug_a} + {r.drug_b} ({'ngoài CSDL' if not r.in_scope else 'trong CSDL nhưng không bắt được'}) — nguồn: {r.source}"
              for r in miss.itertuples()] or ["- (không có)"]
    lines.append("\n> Recall tổng thể thấp nghĩa là CSDL còn hẹp: phải hiển thị rõ cho người dùng rằng 'không có cảnh báo' KHÔNG đồng nghĩa với an toàn.")
    text = "\n".join(lines)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
