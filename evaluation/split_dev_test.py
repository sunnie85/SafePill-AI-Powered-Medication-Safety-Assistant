"""
Chia ảnh thành dev (70%) và test (30%), phân tầng theo condition, cố định seed để tái lập.
    python evaluation/split_dev_test.py --gold evaluation/data/ocr_gold.csv --out evaluation/data
Sinh split_dev.txt và split_test.txt. QUY TẮC: chỉnh prompt/ngưỡng chỉ dựa trên dev; test chỉ chạy 1 lần cuối.
"""
import argparse
import random
from pathlib import Path

import pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument("--gold", required=True)
ap.add_argument("--out", default="evaluation/data")
ap.add_argument("--seed", type=int, default=42)
ap.add_argument("--test-frac", type=float, default=0.3)
a = ap.parse_args()

g = pd.read_csv(a.gold, dtype=str).drop_duplicates("image_id")
rng = random.Random(a.seed)
dev, test = [], []
for cond, grp in g.groupby("condition"):
    ids = sorted(grp["image_id"])
    rng.shuffle(ids)
    n_test = max(1, round(len(ids) * a.test_frac)) if len(ids) >= 2 else 0
    test += ids[:n_test]
    dev += ids[n_test:]
out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
(out / "split_dev.txt").write_text("\n".join(sorted(dev)) + "\n", encoding="utf-8")
(out / "split_test.txt").write_text("\n".join(sorted(test)) + "\n", encoding="utf-8")
print(f"dev={len(dev)} ảnh, test={len(test)} ảnh (seed={a.seed})")
