"""
Đánh giá OCR đơn thuốc của SafePill.

Cách dùng:
    python eval_ocr.py --gold data/ocr_gold.csv --pred results/ocr_pred.csv --out results/ocr_report.md

gold.csv  : image_id, condition, drug_name, strength, dose
            (mỗi dòng = 1 thuốc trên ảnh; condition ví dụ: tot, mo, thieu_sang, choi, nghieng, bi_cat, viet_tay)
pred.csv  : image_id, drug_name, strength, dose, uncertain
            (uncertain = có/không, lấy từ trường "Chưa chắc chắn" của app)
strength có thể để trống: script sẽ tự tách hàm lượng (vd "500mg") từ drug_name.

Chỉ số an toàn quan trọng nhất: "flag recall" = trong các dòng AI đọc SAI, bao nhiêu % đã được
gắn cờ "Chưa chắc chắn". Số dòng sai mà KHÔNG gắn cờ ("lỗi im lặng") là thứ nguy hiểm nhất.
"""
import argparse
import difflib
import math
import re
import unicodedata
from pathlib import Path

import pandas as pd

STRENGTH_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(mg|mcg|µg|g|ml|iu)\b", re.I)
MATCH_THRESHOLD = 0.8  # độ giống tối thiểu để coi 2 tên là "cùng 1 thuốc" (sai chính tả vẫn tính là tìm thấy)


def strip_accents(s) -> str:
    s = unicodedata.normalize("NFD", str(s))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.replace("đ", "d").replace("Đ", "D")


def split_name_strength(name, strength=""):
    name = "" if pd.isna(name) else str(name)
    strength = "" if pd.isna(strength) else str(strength)
    m = STRENGTH_RE.search(name)
    if not strength.strip() and m:
        strength = m.group(0)
    base = STRENGTH_RE.sub(" ", name)
    return base, strength


def norm_name(s) -> str:
    return " ".join(re.sub(r"[^a-z\s]", " ", strip_accents(s).lower()).split())


def norm_strength(s) -> str:
    m = STRENGTH_RE.search("" if pd.isna(s) else str(s))
    return f"{m.group(1).replace(',', '.')}{m.group(2).lower()}" if m else ""


def norm_dose(s) -> str:
    s = strip_accents("" if pd.isna(s) else s).lower()
    s = s.replace("vien", "v").replace("goi", "g_").replace("nang", "n_")
    return re.sub(r"[^a-z0-9.,]", "", s).replace(",", ".")


def is_true(x) -> bool:
    return str(x).strip().lower() in ("có", "co", "true", "1", "yes", "y")


def wilson(k, n, z=1.96):
    if n == 0:
        return 0.0, 0.0
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    a = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (c - a) / d, (c + a) / d


def fmt(k, n) -> str:
    if n == 0:
        return "n/a"
    lo, hi = wilson(k, n)
    return f"{k / n:.1%} ({k}/{n}; KTC95% {lo:.0%}-{hi:.0%})"


def prep(df, has_condition=False):
    df = df.copy()
    for col in ("strength", "dose"):
        if col not in df:
            df[col] = ""
    pairs = [split_name_strength(n, s) for n, s in zip(df["drug_name"], df["strength"])]
    df["_name"] = [norm_name(p[0]) for p in pairs]
    df["_strength"] = [norm_strength(p[1]) for p in pairs]
    df["_dose"] = [norm_dose(d) for d in df["dose"]]
    df = df[df["_name"] != ""]
    return df


def evaluate(gold: pd.DataFrame, pred: pd.DataFrame):
    gold, pred = prep(gold), prep(pred)
    if "uncertain" not in pred:
        pred["uncertain"] = ""
    pred["_unc"] = pred["uncertain"].map(is_true)
    gold_rows, spurious_rows = [], []

    for image_id, g in gold.groupby("image_id"):
        cond = g["condition"].iloc[0] if "condition" in g else "all"
        p = pred[pred["image_id"] == image_id]
        cand = []
        for gi, grow in g.iterrows():
            for pi, prow in p.iterrows():
                r = difflib.SequenceMatcher(None, grow["_name"], prow["_name"]).ratio()
                if r >= MATCH_THRESHOLD:
                    cand.append((r, gi, pi))
        cand.sort(reverse=True)
        used_g, used_p, match = set(), set(), {}
        for r, gi, pi in cand:
            if gi in used_g or pi in used_p:
                continue
            used_g.add(gi), used_p.add(pi)
            match[gi] = pi

        for gi, grow in g.iterrows():
            rec = {"image_id": image_id, "condition": cond, "found": gi in match}
            if gi in match:
                prow = p.loc[match[gi]]
                rec["name_ok"] = grow["_name"] == prow["_name"]
                rec["strength_ok"] = grow["_strength"] == prow["_strength"]
                rec["dose_ok"] = grow["_dose"] == prow["_dose"]
                rec["all_ok"] = rec["name_ok"] and rec["strength_ok"] and rec["dose_ok"]
                rec["flagged"] = bool(prow["_unc"])
            gold_rows.append(rec)

        for pi, prow in p.iterrows():
            if pi not in used_p:  # AI "bịa" ra thuốc không có trên ảnh (hoặc đọc sai tên quá nhiều)
                spurious_rows.append({"image_id": image_id, "condition": cond, "flagged": bool(prow["_unc"])})

    return pd.DataFrame(gold_rows), pd.DataFrame(spurious_rows)


def summarize(g: pd.DataFrame, s: pd.DataFrame) -> dict:
    n = len(g)
    f = g[g["found"]]
    wrong_found = f[~f["all_ok"].astype(bool)]
    wrong_total = len(wrong_found) + len(s)
    flagged_wrong = int(wrong_found["flagged"].sum()) + (int(s["flagged"].sum()) if len(s) else 0)
    silent = wrong_total - flagged_wrong
    return {
        "Số thuốc (gold)": n,
        "Tìm thấy thuốc": fmt(len(f), n),
        "Đúng tên": fmt(int(f["name_ok"].sum()), n),
        "Đúng hàm lượng": fmt(int(f["strength_ok"].sum()), n),
        "Đúng liều dùng": fmt(int(f["dose_ok"].sum()), n),
        "Đúng cả 3 (tên+hàm lượng+liều)": fmt(int(f["all_ok"].sum()), n),
        "Thuốc 'bịa'/sai tên nặng": len(s),
        "Flag recall (dòng sai được gắn cờ)": fmt(flagged_wrong, wrong_total),
        "Lỗi im lặng (sai, KHÔNG gắn cờ)": f"{silent} / {n} thuốc ({(silent / n if n else 0):.1%})",
    }


def to_markdown(rows: dict) -> str:
    out = ["| Chỉ số | Kết quả |", "|---|---|"]
    out += [f"| {k} | {v} |" for k, v in rows.items()]
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", required=True)
    ap.add_argument("--pred", required=True)
    ap.add_argument("--out", default="results/ocr_report.md")
    ap.add_argument("--status", help="file *_status.csv do run_ocr_batch.py sinh ra (để loại ảnh bị từ chối)")
    a = ap.parse_args()
    gold, pred = pd.read_csv(a.gold, dtype=str), pd.read_csv(a.pred, dtype=str)
    reject_lines = []
    if a.status:
        st = pd.read_csv(a.status, dtype=str)
        rejected = set(st.loc[st["status"] == "rejected", "image_id"])
        errors = set(st.loc[st["status"] == "error", "image_id"])
        n_all = gold["image_id"].nunique()
        img_cond = gold.drop_duplicates("image_id").set_index("image_id")["condition"]
        reject_lines = [f"- Ảnh bị TỪ CHỐI do chất lượng (hành vi an toàn, không tính là lỗi OCR): {len(rejected)}/{n_all}",
                        f"- Ảnh lỗi kỹ thuật khi gọi AI: {len(errors)}/{n_all}"]
        for cond, k in img_cond[img_cond.index.isin(rejected)].value_counts().items():
            tot = int((img_cond == cond).sum())
            reject_lines.append(f"  - {cond}: {k}/{tot} ảnh bị từ chối")
        gold = gold[~gold["image_id"].isin(rejected)]
    g, s = evaluate(gold, pred)

    parts = ["# Báo cáo đánh giá OCR SafePill\n",
             f"- Số ảnh đưa vào chấm: {gold['image_id'].nunique()} | Số thuốc gold: {len(g)}", *reject_lines, "",
             "## Tổng hợp\n", to_markdown(summarize(g, s)), "\n## Theo điều kiện ảnh\n"]
    for cond, gg in g.groupby("condition"):
        ss = s[s["condition"] == cond] if len(s) else s
        parts += [f"### {cond}\n", to_markdown(summarize(gg, ss)), ""]
    parts.append("\n> Lưu ý: tập nhỏ nên khoảng tin cậy rộng; không dùng kết quả này để khẳng định độ an toàn lâm sàng.")
    text = "\n".join(parts)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
