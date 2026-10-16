"""
safepill_core.py: logic thuần của SafePill (KHÔNG import streamlit).
Tách ra để: (1) chạy test/đánh giá tự động, (2) người chấm đọc logic an toàn dễ hơn.
"""
import difflib
import json
import re
import unicodedata
from urllib.parse import urlparse

import numpy as np

TRUSTED_MEDICAL_DOMAINS = (
    "drugs.com", "medlineplus.gov", "nih.gov", "fda.gov", "who.int",
    "mayoclinic.org", "cdc.gov", "rxlist.com", "webmd.com",
)


def extract_json_array(raw_text: str):
    cleaned = raw_text.strip()
    cleaned = re.sub(r"^```json", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = cleaned.replace("```", "").strip()
    match = re.search(r"\[.*\]", cleaned, re.DOTALL)
    if match:
        cleaned = match.group(0)
    return json.loads(cleaned)


PRESCRIPTION_VISION_PROMPT = '''
Bạn là chuyên gia bóc tách dữ liệu y tế. Phân tích hình ảnh này (đơn thuốc, vỉ thuốc, hoặc trang hồ sơ
bệnh án có kê đơn thuốc) và trả về DUY NHẤT một mảng JSON hợp lệ, không kèm markdown hay giải thích thêm,
theo đúng cấu trúc:
[
    {
        "Tên thuốc": "...",
        "Liều lượng": "...",
        "Thời điểm": "Sáng|Trưa|Chiều|Tối hoặc giờ cụ thể HH:MM",
        "Loại": "...",
        "Màu sắc": "màu chủ đạo của viên thuốc quan sát được, ví dụ: trắng, đỏ, vàng, xanh (để trống nếu không thấy rõ)",
        "Hình dạng": "hình dạng viên thuốc quan sát được: tròn | oval | viên nén | vuông | con nhộng (để trống nếu không rõ)",
        "Nơi khám bệnh": "tên bệnh viện/phòng khám ghi trên đơn (để trống nếu không thấy)",
        "Bác sĩ điều trị": "tên bác sĩ kê đơn ghi trên đơn (để trống nếu không thấy)",
        "Nơi cấp thuốc": "tên nhà thuốc/quầy thuốc cấp phát (để trống nếu không thấy)",
        "Lời dặn": "lời dặn của bác sĩ ghi trên đơn, ví dụ: uống sau khi ăn, tránh nắng, không dùng chung với rượu (để trống nếu không thấy)",
        "Chưa chắc chắn": "có nếu chữ mờ/khó đọc hoặc bạn không chắc về tên thuốc/liều lượng, ngược lại ghi không"
    }
]
Nếu chữ mờ hoặc khó đọc, KHÔNG được đoán tên thuốc hay liều lượng: hãy để trống trường đó và đặt "Chưa chắc chắn": "có". Chỉ ghi những gì nhìn thấy rõ trong ảnh.Trường "Màu sắc" và "Hình dạng" giúp người già không đọc được chữ nhỏ vẫn nhận diện được thuốc qua hình ảnh minh hoạ.
Các trường "Nơi khám bệnh", "Bác sĩ điều trị", "Nơi cấp thuốc" thường lặp lại giống nhau cho mọi loại
thuốc trong CÙNG một đơn/toa — nếu đơn chỉ ghi thông tin này một lần ở đầu hoặc cuối trang, hãy áp dụng
lại giá trị đó cho TẤT CẢ các thuốc được bóc tách từ đơn đó.
Nếu ảnh không chứa thông tin đơn thuốc/thuốc nào, hãy trả về mảng JSON rỗng: []
Nếu ảnh bị cắt mép, bị che hoặc thiếu chữ khiến bạn KHÔNG chắc đã thấy đủ danh sách thuốc, hãy thêm vào CUỐI mảng
một phần tử: {"Tên thuốc": "", "Liều lượng": "", "Chưa chắc chắn": "có", "Lời dặn": "ẢNH CÓ THỂ THIẾU THUỐC, HÃY SOÁT LẠI VỚI ĐƠN GỐC"}
'''


DEFAULT_SOURCE_NOTE = "Dược thư Quốc gia Việt Nam; Drugs.com Interaction Checker"
DEFAULT_SOURCE_NOTE_EN = "Vietnamese National Pharmacopoeia (Dược thư Quốc gia Việt Nam); Drugs.com Interaction Checker"


INTERACTION_DATABASE = {
    "Aspirin": {"conflict": ["Ibuprofen", "Warfarin", "Naproxen", "Clopidogrel"],
                "severity": "Cao", "effect": "Tăng nguy cơ xuất huyết tiêu hóa nghiêm trọng.",
                "severity_en": "High", "effect_en": "Increased risk of serious gastrointestinal bleeding.",
                "nguon": "Dược thư Quốc gia Việt Nam; Drugs.com (Aspirin Interactions)",
                "nguon_en": "Vietnamese National Pharmacopoeia; Drugs.com (Aspirin Interactions)"},
    "Ibuprofen": {"conflict": ["Aspirin", "Corticoid", "Enalapril", "Losartan", "Furosemide"],
                  "severity": "Cao", "effect": "Giảm hiệu quả hạ huyết áp, tăng độc tính thận.",
                  "severity_en": "High",
                  "effect_en": "Reduced blood-pressure-lowering effect and increased kidney toxicity.",
                  "nguon": "Dược thư Quốc gia Việt Nam; Drugs.com (Ibuprofen Interactions)",
                  "nguon_en": "Vietnamese National Pharmacopoeia; Drugs.com (Ibuprofen Interactions)"},
    "Paracetamol": {"conflict": ["Alcohol", "Leflunomide", "Warfarin"],
                    "severity": "Trung bình", "effect": "Tăng độc tính và nguy cơ hủy hoại tế bào gan.",
                    "severity_en": "Moderate",
                    "effect_en": "Increased toxicity and risk of liver cell damage.",
                    "nguon": "Dược thư Quốc gia Việt Nam; Drugs.com (Acetaminophen Interactions)",
                    "nguon_en": "Vietnamese National Pharmacopoeia; Drugs.com (Acetaminophen Interactions)"},
    "Metformin": {"conflict": ["Contrast dye", "Cimetidine", "Alcohol"],
                  "severity": "Nghiêm trọng", "effect": "Tăng nguy cơ nhiễm toan lactic cấp tính.",
                  "severity_en": "Severe",
                  "effect_en": "Increased risk of acute lactic acidosis.",
                  "nguon": "Dược thư Quốc gia Việt Nam; Drugs.com (Metformin Interactions)",
                  "nguon_en": "Vietnamese National Pharmacopoeia; Drugs.com (Metformin Interactions)"},
    "Warfarin": {"conflict": ["Aspirin", "Paracetamol", "Ibuprofen", "Amiodarone"],
                 "severity": "Nghiêm trọng", "effect": "Tăng nguy cơ chảy máu do tăng tác dụng chống đông.",
                 "severity_en": "Severe",
                 "effect_en": "Increased bleeding risk due to enhanced anticoagulant effect.",
                 "nguon": "Dược thư Quốc gia Việt Nam; Drugs.com (Warfarin Interactions)",
                 "nguon_en": "Vietnamese National Pharmacopoeia; Drugs.com (Warfarin Interactions)"},
    "Simvastatin": {"conflict": ["Amiodarone", "Clarithromycin", "Grapefruit juice"],
                    "severity": "Cao", "effect": "Tăng nguy cơ tiêu cơ vân (rhabdomyolysis).",
                    "severity_en": "High",
                    "effect_en": "Increased risk of rhabdomyolysis (severe muscle breakdown).",
                    "nguon": "Dược thư Quốc gia Việt Nam; Drugs.com (Simvastatin Interactions)",
                    "nguon_en": "Vietnamese National Pharmacopoeia; Drugs.com (Simvastatin Interactions)"},
    "Losartan": {"conflict": ["Ibuprofen", "Potassium", "Spironolactone"],
                 "severity": "Trung bình", "effect": "Tăng kali máu, giảm hiệu quả hạ áp.",
                 "severity_en": "Moderate",
                 "effect_en": "Increased blood potassium and reduced blood-pressure-lowering effect.",
                 "nguon": "Dược thư Quốc gia Việt Nam; Drugs.com (Losartan Interactions)",
                 "nguon_en": "Vietnamese National Pharmacopoeia; Drugs.com (Losartan Interactions)"},
    "Digoxin": {"conflict": ["Furosemide", "Amiodarone"],
                "severity": "Nghiêm trọng", "effect": "Tăng nguy cơ ngộ độc digoxin, rối loạn nhịp tim.",
                "severity_en": "Severe",
                "effect_en": "Increased risk of digoxin toxicity and cardiac arrhythmia.",
                "nguon": "Dược thư Quốc gia Việt Nam; Drugs.com (Digoxin Interactions)",
                "nguon_en": "Vietnamese National Pharmacopoeia; Drugs.com (Digoxin Interactions)"},
    "Clopidogrel": {"conflict": ["Aspirin", "Omeprazole"],
                    "severity": "Trung bình", "effect": "Giảm hiệu quả chống kết tập tiểu cầu.",
                    "severity_en": "Moderate",
                    "effect_en": "Reduced antiplatelet effectiveness.",
                    "nguon": "Dược thư Quốc gia Việt Nam; Drugs.com (Clopidogrel Interactions)",
                    "nguon_en": "Vietnamese National Pharmacopoeia; Drugs.com (Clopidogrel Interactions)"},
}


def build_symmetric_lookup(db: dict) -> dict:
    lookup = {k: dict(v) for k, v in db.items()}
    for drug, info in db.items():
        for other in info["conflict"]:
            if other not in lookup:
                lookup[other] = {"conflict": [], "severity": info["severity"], "effect": info["effect"],
                                  "severity_en": info.get("severity_en"), "effect_en": info.get("effect_en"),
                                  "nguon": info.get("nguon", DEFAULT_SOURCE_NOTE),
                                  "nguon_en": info.get("nguon_en", DEFAULT_SOURCE_NOTE_EN)}
            if drug not in lookup[other]["conflict"]:
                lookup[other]["conflict"].append(drug)
    return lookup


INTERACTION_LOOKUP = build_symmetric_lookup(INTERACTION_DATABASE)
import difflib
BRAND_TO_GENERIC = {"panadol": "Paracetamol", "efferalgan": "Paracetamol", "hapacol": "Paracetamol"}
def normalize_drug_name(raw: str):
    """Trả về (tên_chuẩn hoặc None, danh_sách_gợi_ý)."""
    name = _strip_accents(raw or "").lower()
    name = re.sub(r"\d+([.,]\d+)?\s*(mg|mcg|µg|g|ml|iu)\b", " ", name)   # bỏ hàm lượng
    name = re.sub(r"\b(vien|nen|nang|goi|ong)\b", " ", name)             # bỏ dạng bào chế
    name = " ".join(re.sub(r"[^a-z\s]", " ", name).split())
    if not name:
        return None, []
    if name in BRAND_TO_GENERIC:
        return BRAND_TO_GENERIC[name], []
    known = {d.lower(): d for d in set(INTERACTION_LOOKUP) | set(VN_FOOD_HERB_DATABASE)}
    if name in known:
        return known[name], []
    return None, [known[k] for k in difflib.get_close_matches(name, known, n=3, cutoff=0.7)]

def find_unidentified_drugs(med_data: list) -> list:
    return [m["Tên thuốc"] for m in med_data
            if m.get("Tên thuốc") and normalize_drug_name(m["Tên thuốc"])[0] is None]


def check_interaction(drug_a: str, drug_b: str):
    a, _ = normalize_drug_name(drug_a)
    b, _ = normalize_drug_name(drug_b)
    if not a or not b:
        return None
    info = INTERACTION_LOOKUP.get(a)
    if info and b in info["conflict"]:
        return {"thuoc_1": a, "thuoc_2": b, "severity": info["severity"], "effect": info["effect"],
                "severity_en": info.get("severity_en"), "effect_en": info.get("effect_en"),
                "nguon": info.get("nguon", DEFAULT_SOURCE_NOTE),
                "nguon_en": info.get("nguon_en", DEFAULT_SOURCE_NOTE_EN)}
    return None


def scan_cabinet_for_conflicts(med_data: list) -> list:
    names = [m.get("Tên thuốc", "").strip().capitalize() for m in med_data if m.get("Tên thuốc")]
    conflicts = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            result = check_interaction(names[i], names[j])
            if result:
                conflicts.append(result)
    return conflicts


VN_FOOD_HERB_DATABASE = {
    "Paracetamol": [
        {"item": "Rượu bia", "severity": "Cao",
         "effect": "Tăng nguy cơ tổn thương gan cấp tính, đặc biệt khi dùng liều cao kéo dài.",
         "item_en": "Alcohol", "severity_en": "High",
         "effect_en": "Increased risk of acute liver damage, especially with high or prolonged doses.",
         "nguon": "Drugs.com (Acetaminophen + Alcohol); Dược thư Quốc gia Việt Nam",
         "nguon_en": "Drugs.com (Acetaminophen + Alcohol); Vietnamese National Pharmacopoeia"},
    ],
    "Metformin": [
        {"item": "Rượu bia", "severity": "Nghiêm trọng",
         "effect": "Tăng nguy cơ nhiễm toan lactic, có thể đe dọa tính mạng.",
         "item_en": "Alcohol", "severity_en": "Severe",
         "effect_en": "Increased risk of lactic acidosis, which can be life-threatening.",
         "nguon": "Drugs.com (Metformin + Alcohol); Dược thư Quốc gia Việt Nam",
         "nguon_en": "Drugs.com (Metformin + Alcohol); Vietnamese National Pharmacopoeia"},
    ],
    "Warfarin": [
        {"item": "Rau càng cua / rau ngót / cải xoăn (nhiều vitamin K)", "severity": "Trung bình",
         "effect": "Giảm tác dụng chống đông máu, tăng nguy cơ hình thành cục máu đông.",
         "item_en": "Vitamin K–rich leafy greens (e.g., watercress, katuk, kale)",
         "severity_en": "Moderate",
         "effect_en": "Reduced anticoagulant effect, increasing the risk of blood clots.",
         "nguon": "Drugs.com (Warfarin + Vitamin K foods); Dược thư Quốc gia Việt Nam",
         "nguon_en": "Drugs.com (Warfarin + Vitamin K foods); Vietnamese National Pharmacopoeia"},
        {"item": "Thuốc nam / thực phẩm chức năng (đương quy, nhân sâm, tỏi cô đặc...)", "severity": "Cao",
         "effect": "Có thể tăng hoặc giảm tác dụng chống đông không kiểm soát, tăng nguy cơ chảy máu.",
         "item_en": "Herbal remedies/supplements (e.g., dong quai, ginseng, concentrated garlic)",
         "severity_en": "High",
         "effect_en": "May unpredictably increase or decrease the anticoagulant effect, raising bleeding risk.",
         "nguon": "Drugs.com (Warfarin herbal interactions); khuyến cáo Bệnh viện Bạch Mai",
         "nguon_en": "Drugs.com (Warfarin herbal interactions); Bach Mai Hospital advisory"},
    ],
    "Simvastatin": [
        {"item": "Nước ép bưởi / bưởi", "severity": "Cao",
         "effect": "Tăng nồng độ thuốc trong máu, tăng nguy cơ tiêu cơ vân (rhabdomyolysis).",
         "item_en": "Grapefruit juice / grapefruit", "severity_en": "High",
         "effect_en": "Increased blood drug levels, raising the risk of rhabdomyolysis.",
         "nguon": "Drugs.com (Simvastatin + Grapefruit); FDA Consumer Update",
         "nguon_en": "Drugs.com (Simvastatin + Grapefruit); FDA Consumer Update"},
    ],
    "Aspirin": [
        {"item": "Rượu bia", "severity": "Cao",
         "effect": "Tăng nguy cơ xuất huyết tiêu hóa.",
         "item_en": "Alcohol", "severity_en": "High",
         "effect_en": "Increased risk of gastrointestinal bleeding.",
         "nguon": "Drugs.com (Aspirin + Alcohol); Dược thư Quốc gia Việt Nam",
         "nguon_en": "Drugs.com (Aspirin + Alcohol); Vietnamese National Pharmacopoeia"},
        {"item": "Gừng, tỏi cô đặc (thực phẩm chức năng liều cao)", "severity": "Trung bình",
         "effect": "Tăng tác dụng chống kết tập tiểu cầu, tăng nguy cơ chảy máu.",
         "item_en": "Ginger, concentrated garlic (high-dose supplements)",
         "severity_en": "Moderate",
         "effect_en": "Increased antiplatelet effect, raising bleeding risk.",
         "nguon": "Drugs.com (Aspirin herbal interactions)",
         "nguon_en": "Drugs.com (Aspirin herbal interactions)"},
    ],
    "Digoxin": [
        {"item": "Cam thảo (thuốc nam)", "severity": "Cao",
         "effect": "Gây hạ kali máu, tăng nguy cơ ngộ độc digoxin.",
         "item_en": "Licorice root (herbal remedy)", "severity_en": "High",
         "effect_en": "Causes low blood potassium, increasing the risk of digoxin toxicity.",
         "nguon": "Drugs.com (Digoxin + Licorice); Dược thư Quốc gia Việt Nam",
         "nguon_en": "Drugs.com (Digoxin + Licorice); Vietnamese National Pharmacopoeia"},
    ],
    "Clopidogrel": [
        {"item": "Rượu bia", "severity": "Trung bình",
         "effect": "Tăng nguy cơ kích ứng và chảy máu đường tiêu hóa.",
         "item_en": "Alcohol", "severity_en": "Moderate",
         "effect_en": "Increased risk of gastrointestinal irritation and bleeding.",
         "nguon": "Drugs.com (Clopidogrel + Alcohol)",
         "nguon_en": "Drugs.com (Clopidogrel + Alcohol)"},
    ],
}


def check_food_herb_conflicts(med_data: list) -> list:
    results = []
    for m in med_data:
        name, _ = normalize_drug_name(m.get("Tên thuốc", ""))
        if name in VN_FOOD_HERB_DATABASE:
            for warn in VN_FOOD_HERB_DATABASE[name]:
                results.append({"thuoc": name, **warn})
    return results


def _strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text)
    without_marks = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    return without_marks.replace("đ", "d").replace("Đ", "D")


def _fuzzy_food_item_match(user_input: str, item_field: str) -> bool:
    if not user_input or not user_input.strip():
        return False
    ui = _strip_accents(user_input).strip().lower()
    for part in re.split(r"[/,]", item_field):
        p = _strip_accents(part).strip().lower()
        p_main = re.sub(r"\(.*?\)", "", p).strip()
        if not p_main:
            continue
        if ui in p_main or p_main in ui:
            return True
    return False


def check_food_herb_pair(input_a: str, input_b: str) -> list:
    results = []
    a_clean, b_clean = input_a.strip(), input_b.strip()
    a_key = normalize_drug_name(a_clean)[0] or a_clean.capitalize()
    b_key = normalize_drug_name(b_clean)[0] or b_clean.capitalize()
    if a_key in VN_FOOD_HERB_DATABASE:
        for warn in VN_FOOD_HERB_DATABASE[a_key]:
            if _fuzzy_food_item_match(b_clean, warn["item"]):
                results.append({"thuoc": a_key, **warn})

    if b_key in VN_FOOD_HERB_DATABASE:
        for warn in VN_FOOD_HERB_DATABASE[b_key]:
            if _fuzzy_food_item_match(a_clean, warn["item"]):
                results.append({"thuoc": b_key, **warn})

    return results


# =====================================================================================
# ĐỘ TIN CẬY & KIỂM TRA AN TOÀN (mới)
# =====================================================================================
DB_LAST_REVIEWED = "2026-10-15"   # CẬP NHẬT mỗi lần rà soát lại cơ sở dữ liệu tương tác
DB_REVIEWED_BY = "Nhóm phát triển (chưa có dược sĩ thẩm định)"  # ĐỔI khi có dược sĩ rà soát

SAFETY_PROMPT_RULES = (
    "QUY TẮC AN TOÀN: Chỉ khẳng định điều có trong dữ liệu FDA/nguồn đã tìm được. "
    "Nếu không có căn cứ, hãy nói rõ \"Tôi không tìm thấy căn cứ đáng tin cậy\". "
    "KHÔNG khuyên tự ý ngưng thuốc, đổi liều hoặc kết hợp thêm thuốc. "
    "KHÔNG được nói rằng các tương tác đã phát hiện ở trên là vô hại. "
    "Với câu hỏi về liều hoặc tương tác nghiêm trọng, luôn kết luận bằng việc hỏi bác sĩ hoặc dược sĩ."
)


def is_trusted_medical_source(uri: str, title: str = "") -> bool:
    """So khớp theo hostname (không phải chuỗi con) + tiêu đề nguồn.
    Link grounding của Gemini thường là link chuyển hướng, tên miền thật nằm ở title."""
    def match(host: str) -> bool:
        host = (host or "").lower().strip()
        return any(host == d or host.endswith("." + d) for d in TRUSTED_MEDICAL_DOMAINS)
    return match(urlparse(uri or "").hostname or "") or match(title or "")


def check_image_quality(pil_img, blur_min: float = 60.0, dark_max: float = 60.0,
                        bright_max: float = 235.0, min_side: int = 600):
    """Trả về (nghiêm_trọng, nhẹ). Nghiêm trọng: chặn. Nhẹ: vẫn đọc nhưng ép 'chưa chắc chắn'.
    Ngưỡng cần được hiệu chỉnh bằng bộ ảnh dev (xem evaluation/)."""
    severe, mild = [], []
    if min(pil_img.size) < min_side:
        severe.append("Ảnh độ phân giải quá thấp, hãy chụp gần hơn.")
    img = pil_img.copy()
    img.thumbnail((1000, 1000))
    g = np.asarray(img.convert("L"), dtype=np.float32)
    if g.shape[0] < 3 or g.shape[1] < 3:
        return severe + ["Ảnh quá nhỏ."], mild
    lap = (-4 * g[1:-1, 1:-1] + g[:-2, 1:-1] + g[2:, 1:-1] + g[1:-1, :-2] + g[1:-1, 2:])
    v = float(lap.var())
    if v < blur_min * 0.5:
        severe.append("Ảnh rất mờ, hãy chụp lại gần và giữ yên máy.")
    elif v < blur_min:
        mild.append("Ảnh hơi mờ.")
    m = float(g.mean())
    if m < dark_max * 0.6:
        severe.append("Ảnh quá tối, hãy chụp nơi nhiều ánh sáng hơn.")
    elif m < dark_max:
        mild.append("Ảnh thiếu sáng.")
    if m > bright_max:
        mild.append("Ảnh bị chói, hãy tránh ánh sáng phản chiếu.")
    return severe, mild


def read_prescription_with_gemini(client, pil_img, model: str = "gemini-flash-latest"):
    """Gọi Gemini đọc đơn thuốc, trả về list dict. Dùng chung cho app và run_ocr_batch.py."""
    resp = client.models.generate_content(model=model, contents=[pil_img, PRESCRIPTION_VISION_PROMPT])
    meds = extract_json_array(resp.text)
    if not isinstance(meds, list):
        raise ValueError("AI không trả về danh sách thuốc hợp lệ.")
    return meds


def interaction_coverage_note(med_data: list, lang: str = "vi") -> str:
    names = [m["Tên thuốc"] for m in med_data if m.get("Tên thuốc")]
    known = [n for n in names if normalize_drug_name(n)[0]]
    n_pairs = sum(len(v["conflict"]) for v in INTERACTION_DATABASE.values())
    if lang == "en":
        return (f"Checked {len(known)}/{len(names)} medications against a small database of about {n_pairs} "
                f"interaction pairs (reviewed {DB_LAST_REVIEWED}; {DB_REVIEWED_BY}). "
                f"**No warning does NOT mean safe.** Please ask your doctor or pharmacist, "
                f"especially if you take several medications.")
    return (f"Đã đối chiếu {len(known)}/{len(names)} thuốc với cơ sở dữ liệu nhỏ gồm khoảng {n_pairs} cặp "
            f"tương tác (rà soát {DB_LAST_REVIEWED}; {DB_REVIEWED_BY}). "
            f"**Không thấy cảnh báo KHÔNG có nghĩa là an toàn.** "
            f"Hãy hỏi bác sĩ/dược sĩ, nhất là khi dùng nhiều loại thuốc.")


def assess_answer_confidence(has_fda: bool, n_trusted_links: int, lang: str = "vi"):
    """Độ tin cậy theo CĂN CỨ THỰC TẾ (dữ liệu FDA + nguồn uy tín), không theo lời AI tự nhận.
    Trả về (mức, banner|None); mức thuộc {'cao','trung bình','thấp'}."""
    en = lang == "en"
    if has_fda and n_trusted_links >= 1:
        return "cao", None
    if has_fda or n_trusted_links >= 1:
        return "trung bình", (
            "⚠️ Evidence is limited (only one kind of reference source). Please confirm with your doctor or pharmacist."
            if en else
            "⚠️ Căn cứ còn hạn chế (chỉ có một loại nguồn đối chiếu). Hãy xác nhận lại với bác sĩ/dược sĩ.")
    return "thấp", (
        "🔴 **No reputable medical source could be found to verify this answer.** The text below is general "
        "information only; do NOT use it to change doses, stop or combine medications. Please ask your doctor or pharmacist."
        if en else
        "🔴 **Không tìm được nguồn y khoa uy tín để đối chiếu cho câu trả lời này.** Nội dung bên dưới chỉ mang "
        "tính tham khảo chung, KHÔNG nên dùng để đổi liều, ngưng thuốc hay kết hợp thuốc. "
        "Vui lòng hỏi bác sĩ/dược sĩ.")


def format_confidence_block(level: str, banner, lang: str = "vi") -> str:
    label = "Evidence confidence" if lang == "en" else "Độ tin cậy căn cứ"
    text = f"**{label}: {level}**\n\n"
    if banner:
        text += banner + "\n\n"
    return text


def validate_pending_rows(rows: list):
    """rows: [{'keep': bool, 'name': str, 'dose': str}] -> (blocking, soft) là 2 danh sách thông báo.
    blocking: chặn lưu. soft: chỉ nhắc."""
    blocking, soft = [], []
    for i, r in enumerate(rows, start=1):
        if not r.get("keep"):
            continue
        name, dose = str(r.get("name", "")).strip(), str(r.get("dose", "")).strip()
        if not name or not dose:
            blocking.append(f"Dòng {i}: thiếu tên thuốc hoặc liều lượng.")
            continue
        if not re.search(r"\d|nửa|nua|half", dose.lower()):
            soft.append(f"Dòng {i}: liều '{dose}' không có con số, hãy kiểm tra lại.")
        canon, sugg = normalize_drug_name(name)
        if canon is None:
            soft.append(f"Dòng {i}: '{name}' chưa có trong dữ liệu tương tác"
                        + (f" (có phải: {', '.join(sugg)}?)" if sugg else "") + ".")
    return blocking, soft
