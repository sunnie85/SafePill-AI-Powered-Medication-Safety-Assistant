"""
Tổng hợp thử nghiệm người dùng.
    python evaluation/user_study/user_study_summary.py --obs observation.csv --sus sus.csv --out results/user_study_report.md

observation.csv: participant_id, age_group, n_meds_daily, task_time_s, found_seeded_name, found_seeded_strength,
                 found_interaction, help_requests, comments        (các cột found_* = 1/0)
sus.csv        : participant_id, q1..q10 (mỗi câu 1-5, theo đúng thứ tự bảng SUS chuẩn)
"""
import argparse
import math
from pathlib import Path

import pandas as pd


def wilson(k, n, z=1.96):
    if n == 0:
        return 0.0, 0.0
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (c - h) / d, (c + h) / d


def rate(s):
    s = pd.to_numeric(s, errors="coerce").dropna()
    k, n = int(s.sum()), len(s)
    lo, hi = wilson(k, n)
    return f"{k / n:.0%} ({k}/{n}; KTC95% {lo:.0%}-{hi:.0%})" if n else "n/a"


def sus(row):
    q = [pd.to_numeric(row[f"q{i}"]) for i in range(1, 11)]
    odd = sum(x - 1 for x in q[0::2])      # câu 1,3,5,7,9
    even = sum(5 - x for x in q[1::2])     # câu 2,4,6,8,10
    return (odd + even) * 2.5


ap = argparse.ArgumentParser()
ap.add_argument("--obs", required=True)
ap.add_argument("--sus")
ap.add_argument("--out", default="evaluation/results/user_study_report.md")
a = ap.parse_args()
o = pd.read_csv(a.obs)
L = ["# Báo cáo thử nghiệm người dùng\n", "| Chỉ số | Kết quả |", "|---|---|",
     f"| Số người tham gia | {len(o)} |",
     f"| Số người ≥60 tuổi (age_group='60+') | {int((o['age_group'].astype(str) == '60+').sum())} |",
     f"| Phát hiện lỗi cài sẵn về TÊN thuốc | {rate(o['found_seeded_name'])} |",
     f"| Phát hiện lỗi cài sẵn về HÀM LƯỢNG | {rate(o['found_seeded_strength'])} |",
     f"| Tìm thấy cảnh báo tương tác | {rate(o['found_interaction'])} |",
     f"| Thời gian hoàn thành (giây): trung vị / TB | {o['task_time_s'].median():.0f} / {o['task_time_s'].mean():.0f} |",
     f"| Số lần cần hỗ trợ (TB) | {o['help_requests'].mean():.1f} |"]
if a.sus:
    s = pd.read_csv(a.sus)
    scores = s.apply(sus, axis=1)
    L += [f"| Điểm SUS: TB ± SD (min–max) | {scores.mean():.1f} ± {scores.std():.1f} ({scores.min():.0f}–{scores.max():.0f}) |"]
    L += ["\n> SUS tham chiếu: 68 là mức trung bình; ≥80 là tốt. Mẫu nhỏ nên chỉ mang tính thăm dò."]
L += ["\n> Đây là thử nghiệm tính khả dụng, KHÔNG phải thử nghiệm lâm sàng."]
Path(a.out).parent.mkdir(parents=True, exist_ok=True)
Path(a.out).write_text("\n".join(L), encoding="utf-8")
print("\n".join(L))
