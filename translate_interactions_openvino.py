# -*- coding: utf-8 -*-
"""
Script CHẠY 1 LẦN TRÊN MÁY LOCAL (không chạy trên Streamlit Cloud) để dịch
INTERACTION_DATABASE và VN_FOOD_HERB_DATABASE từ tiếng Việt sang tiếng Anh,
dùng Intel OpenVINO Toolkit (qua Optimum-Intel) làm engine dịch offline.

Chuẩn bị (chỉ trên máy local, KHÔNG cần thêm vào requirements.txt của app):
    pip install "optimum[openvino]" sentencepiece sacremoses

Cách chạy:
    python translate_interactions_openvino.py

Kết quả: in ra các đoạn code Python (dict "_en") để bạn COPY-PASTE thủ công
vào safepill.py sau khi tự kiểm tra lại thuật ngữ y khoa. KHÔNG tự động ghi
đè file safepill.py — vì thuật ngữ y khoa cần con người rà soát trước khi dùng.
"""

from optimum.intel import OVModelForSeq2SeqLM
from transformers import AutoTokenizer

MODEL_ID = "Helsinki-NLP/opus-mt-vi-en"

print(f"Đang tải & convert model '{MODEL_ID}' sang định dạng OpenVINO IR "
      f"(chỉ chạy 1 lần, các lần sau sẽ dùng cache local)...")

tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
model = OVModelForSeq2SeqLM.from_pretrained(MODEL_ID, export=True)


def translate(text: str) -> str:
    if not text or not text.strip():
        return ""
    inputs = tokenizer(text, return_tensors="pt")
    outputs = model.generate(**inputs, max_new_tokens=200)
    return tokenizer.decode(outputs[0], skip_special_tokens=True)


# ---- Dán dữ liệu cần dịch từ safepill.py vào đây ----
INTERACTION_DATABASE = {
    "Aspirin": {"severity": "Cao", "effect": "Tăng nguy cơ xuất huyết tiêu hóa nghiêm trọng."},
    "Ibuprofen": {"severity": "Cao", "effect": "Giảm hiệu quả hạ huyết áp, tăng độc tính thận."},
    "Paracetamol": {"severity": "Trung bình", "effect": "Tăng độc tính và nguy cơ hủy hoại tế bào gan."},
    "Metformin": {"severity": "Nghiêm trọng", "effect": "Tăng nguy cơ nhiễm toan lactic cấp tính."},
    "Warfarin": {"severity": "Nghiêm trọng", "effect": "Tăng nguy cơ chảy máu do tăng tác dụng chống đông."},
    "Simvastatin": {"severity": "Cao", "effect": "Tăng nguy cơ tiêu cơ vân (rhabdomyolysis)."},
    "Losartan": {"severity": "Trung bình", "effect": "Tăng kali máu, giảm hiệu quả hạ áp."},
    "Digoxin": {"severity": "Nghiêm trọng", "effect": "Tăng nguy cơ ngộ độc digoxin, rối loạn nhịp tim."},
    "Clopidogrel": {"severity": "Trung bình", "effect": "Giảm hiệu quả chống kết tập tiểu cầu."},
}

SEVERITY_MAP = {  # Không cần dịch máy, map cứng cho chuẩn & nhất quán
    "Thấp": "Low", "Trung bình": "Medium", "Cao": "High", "Nghiêm trọng": "Severe",
}

print("\n" + "=" * 70)
print("# ---- Kết quả dịch INTERACTION_DATABASE (copy phần severity_en / effect_en") 
print("# vào đúng từng thuốc tương ứng trong safepill.py) ----")
print("=" * 70)
for drug, info in INTERACTION_DATABASE.items():
    severity_en = SEVERITY_MAP.get(info["severity"], info["severity"])
    effect_en = translate(info["effect"])
    print(f'"{drug}": severity_en="{severity_en}", effect_en="{effect_en}"')

print("\nHoàn tất. Hãy tự đọc lại từng câu effect_en để đảm bảo đúng thuật ngữ y khoa "
      "trước khi dán vào code chính thức.")