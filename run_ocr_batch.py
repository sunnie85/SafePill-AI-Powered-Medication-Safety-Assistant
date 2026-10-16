"""
Chạy OCR hàng loạt bằng ĐÚNG pipeline của app (cùng prompt, cùng kiểm tra chất lượng ảnh).

    export GEMINI_API_KEY="..."        # Windows PowerShell: $env:GEMINI_API_KEY="..."
    python evaluation/run_ocr_batch.py --images evaluation/data/images \
        --split evaluation/data/split_dev.txt --out evaluation/results/ocr_pred_dev.csv

Sinh ra 2 file:
  ocr_pred_dev.csv         : image_id, drug_name, strength, dose, uncertain   (đưa vào eval_ocr.py --pred)
  ocr_pred_dev_status.csv  : image_id, status (accepted/rejected/error), severe, mild   (đưa vào eval_ocr.py --status)
"""
import argparse
import csv
import os
import sys
import time
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "code")]  # safepill_core nằm ở gốc repo (hoặc code/)
from safepill_core import check_image_quality, read_prescription_with_gemini  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", required=True)
    ap.add_argument("--split", help="file .txt mỗi dòng 1 image_id (vd split_dev.txt); bỏ trống = chạy tất cả")
    ap.add_argument("--out", default="evaluation/results/ocr_pred.csv")
    ap.add_argument("--sleep", type=float, default=2.0, help="giây nghỉ giữa các ảnh để tránh vượt hạn mức API")
    a = ap.parse_args()

    from google import genai
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    wanted = None
    if a.split:
        wanted = {l.strip() for l in Path(a.split).read_text(encoding="utf-8").splitlines() if l.strip()}
    paths = sorted(p for p in Path(a.images).iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"))
    out_path = Path(a.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    status_path = out_path.with_name(out_path.stem + "_status.csv")

    preds, status = [], []
    for p in paths:
        image_id = p.stem
        if wanted is not None and image_id not in wanted:
            continue
        img = Image.open(p).convert("RGB")
        severe, mild = check_image_quality(img)
        if severe:
            status.append({"image_id": image_id, "status": "rejected", "severe": " | ".join(severe), "mild": ""})
            print(f"{image_id}: REJECTED ({severe[0]})")
            continue
        try:
            meds = read_prescription_with_gemini(client, img)
        except Exception as e:
            status.append({"image_id": image_id, "status": "error", "severe": "", "mild": str(e)[:200]})
            print(f"{image_id}: ERROR {e}")
            time.sleep(a.sleep)
            continue
        status.append({"image_id": image_id, "status": "accepted", "severe": "", "mild": " | ".join(mild)})
        for m in meds:
            unsure = str(m.get("Chưa chắc chắn", "")).strip().lower() in ("có", "co", "true", "yes")
            preds.append({"image_id": image_id, "drug_name": m.get("Tên thuốc", ""), "strength": "",
                          "dose": m.get("Liều lượng", ""), "uncertain": "có" if (unsure or mild) else "không"})
        print(f"{image_id}: {len(meds)} thuốc" + (" (ảnh hơi kém → ép 'chưa chắc')" if mild else ""))
        time.sleep(a.sleep)

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["image_id", "drug_name", "strength", "dose", "uncertain"])
        w.writeheader(); w.writerows(preds)
    with open(status_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["image_id", "status", "severe", "mild"])
        w.writeheader(); w.writerows(status)
    print(f"\nĐã ghi {out_path} và {status_path}")


if __name__ == "__main__":
    main()
