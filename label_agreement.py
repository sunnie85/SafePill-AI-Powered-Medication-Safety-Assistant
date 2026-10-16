"""
Đo mức đồng thuận giữa 2 người gắn nhãn (ghi kết quả này vào DATASHEET.md).
    python evaluation/label_agreement.py --a data/labels_A.csv --b data/labels_B.csv
Hai file cùng định dạng ocr_gold.csv, chỉ cần chứa các ảnh được gắn nhãn kép.
"""
import argparse
import pandas as pd
from eval_ocr import evaluate, fmt

ap = argparse.ArgumentParser()
ap.add_argument("--a", required=True)
ap.add_argument("--b", required=True)
a = ap.parse_args()
A, B = pd.read_csv(a.a, dtype=str), pd.read_csv(a.b, dtype=str)
B = B[B["image_id"].isin(A["image_id"])]
A = A[A["image_id"].isin(B["image_id"])]
g, s = evaluate(A, B)
f = g[g["found"]]
n = len(g)
print(f"Số ảnh gắn nhãn kép: {A['image_id'].nunique()} | số thuốc theo người A: {n}")
print("Cả hai cùng ghi nhận thuốc :", fmt(len(f), n))
print("Đồng ý đúng tên            :", fmt(int(f['name_ok'].sum()), n))
print("Đồng ý hàm lượng           :", fmt(int(f['strength_ok'].sum()), n))
print("Đồng ý liều dùng           :", fmt(int(f['dose_ok'].sum()), n))
print("Đồng ý cả 3                :", fmt(int(f['all_ok'].sum()), n))
print("Thuốc chỉ người B ghi      :", len(s))
print("→ Các dòng không đồng ý: nhờ người thứ 3 (dược sĩ) quyết định và sửa vào file gold.")
