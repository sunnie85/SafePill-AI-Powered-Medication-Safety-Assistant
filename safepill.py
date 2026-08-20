from urllib import response
import streamlit as st
import streamlit.components.v1 as components
import time
import re
import os
import unicodedata
import hashlib
import json
import io
import base64
import os
import sys
from datetime import datetime, time as dtime, timedelta
from supabase import create_client
from google import genai
from PIL import Image
from openvino_ocr_helper import run_openvino_ocr, parse_offline_ocr_text
try:
    from streamlit_autorefresh import st_autorefresh
    AUTOREFRESH_AVAILABLE = True
except ImportError:
    AUTOREFRESH_AVAILABLE = False
# ---- Mới: kiểu dữ liệu cấu hình công cụ tìm kiếm (grounding) của Gemini, dùng để ----
# yêu cầu AI trích dẫn nguồn uy tín (Drugs.com, Dược thư Quốc gia VN...) khi trả lời.
try:
    from google.genai import types as genai_types
    GEMINI_SEARCH_GROUNDING_AVAILABLE = True
except ImportError:
    GEMINI_SEARCH_GROUNDING_AVAILABLE = False

# ---- Mới: thư viện cho QR khẩn cấp & biểu đồ tuân thủ ----
# Cần thêm vào requirements.txt: qrcode[pil], matplotlib
try:
    import qrcode
    QRCODE_AVAILABLE = True
except ImportError:
    QRCODE_AVAILABLE = False

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
# =====================================================================================
# 1. CẤU HÌNH TRANG
# =====================================================================================
st.set_page_config(
    page_title="SafePill – Trợ Lý Dược Phẩm Thông Minh",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded"
)
# ---- Logo ứng dụng ----
LOGO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo.png")


def render_app_logo(width: int = 60) -> None:
    """Hiển thị logo SafePill; nếu thiếu file thì âm thầm dùng icon dự phòng,
    không để lỗi thiếu ảnh làm sập toàn bộ ứng dụng."""
    if os.path.exists(LOGO_PATH):
        try:
            st.image(LOGO_PATH, width=width)
            return
        except Exception:
            pass
    st.image("https://cdn-icons-png.flaticon.com/512/3022/3022574.png", width=width)
# ---- Mới: áp dụng theme giao diện SafePill (teal-slate) ----
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from theme_snippet import apply_safepill_theme
apply_safepill_theme()

DISCLAIMER = (
    "⚠️ SafePill là công cụ hỗ trợ nhắc nhở & tra cứu thông tin thuốc, "
    "KHÔNG thay thế chẩn đoán hoặc chỉ định của bác sĩ/dược sĩ. "
    "Trong trường hợp khẩn cấp, vui lòng liên hệ cơ sở y tế gần nhất."
)

# =====================================================================================
# 1B. MỚI: HỆ THỐNG ĐA NGÔN NGỮ (i18n) — Việt / English
# =====================================================================================
# Cách mở rộng: thêm 1 key mới vào CẢ HAI dict "vi" và "en" bên dưới, rồi gọi tr("ten_key")
# ở bất kỳ đâu trong UI. Nếu thiếu key ở "en", tr() sẽ tự rơi về bản tiếng Việt để tránh vỡ giao diện.
LANGUAGE_OPTIONS = {"vi": "Tiếng Việt", "en": "English"}

TRANSLATIONS = {
    "vi": {
        # ---- Onboarding ----
        "app_title": "💊 SafePill",
        "app_tagline": "Trợ lý dược phẩm thông minh — quét đơn thuốc, phát hiện tương tác nguy hiểm, "
                        "nhắc uống thuốc đúng giờ.",
        "onboarding_card_title": "Giải Pháp Số Hóa Y Tế",
        "onboarding_card_desc": "Quét đơn thuốc bằng camera, tự động phát hiện tương tác thuốc nguy hiểm "
                                 "và nhắc bạn uống thuốc đúng giờ mỗi ngày.",
        "start_button": "BẮT ĐẦU SỬ DỤNG ➔",
        "disclaimer": DISCLAIMER,

        # ---- Đăng nhập / Đăng ký ----
        "auth_header": "🔐 Đăng nhập / Đăng ký",
        "tab_login": "🔑 Đăng nhập",
        "tab_register": "🆕 Đăng ký nhanh (5 chạm)",
        "login_method_label": "Mở khóa bằng:",
        "login_pin": "Mã PIN 4 số",
        "login_face": "Khuôn mặt (FaceID)",
        "phone_label": "Số điện thoại",
        "phone_placeholder": "09xxxxxxxx",
        "pin_label": "Mã PIN (4 số)",
        "N/A":"Chưa rõ",
        "login_button": "Đăng nhập",
        "login_warning_empty": "⚠️ Vui lòng nhập đầy đủ số điện thoại và mã PIN.",
        "login_authenticating": "Đang xác thực...",
        "login_success": "✅ Đăng nhập thành công!",
        "login_wrong_pin": "❌ Mã PIN không chính xác.",
        "login_phone_not_found": "❌ Số điện thoại chưa được đăng ký.",
        "login_db_error": "Lỗi kết nối cơ sở dữ liệu:",
        "face_login_hint": "📷 Nhìn thẳng vào camera để đối chiếu khuôn mặt đã đăng ký.",
        "face_login_capture": "Chụp ảnh xác thực",
        "face_login_matching": "🔍 Đang đối chiếu dữ liệu sinh trắc học...",
        "face_login_bad_image": "❌ Không xử lý được ảnh vừa chụp. Vui lòng thử lại với ảnh rõ nét hơn.",
        "face_login_missing_col": "⚠️ Bảng dữ liệu chưa có cột lưu FaceID (face_data/face_hash). "
                                   "Hãy chạy migration SQL để thêm cột trước khi dùng FaceID.",
        "face_login_no_accounts": "⚠️ Chưa có tài khoản nào đăng ký FaceID. "
                                   "Hãy đăng nhập bằng mã PIN, sau đó bật FaceID trong phần đăng ký.",
        "face_login_welcome": "✅ Xác thực FaceID thành công! Chào mừng",
        "face_login_profile_fail": "❌ Không thể tải hồ sơ người dùng, vui lòng thử lại.",
        "face_login_no_match": "❌ Không tìm thấy khuôn mặt khớp trong hệ thống. "
                                "Vui lòng đăng nhập bằng mã PIN hoặc đăng ký tài khoản mới.",
        "face_login_error": "Lỗi xác thực FaceID:",

        "register_caption": "Điền đầy đủ 4 trường bắt buộc (số điện thoại, họ tên, mã PIN, nhóm máu) — "
                             "FaceID vẫn là tuỳ chọn, có thể bật ngay hoặc bổ sung sau.",
        "full_name_label": "👤 Họ và tên",
        "full_name_placeholder": "Nguyễn Văn A",
        "pin_create_label": "🔢 Tạo mã PIN (4 số)",
        "pin_show_checkbox": "Hiện",
        "pin_show_help": "Hiện mã PIN để tự kiểm tra, không cần nhập lại lần 2 (rút gọn thao tác)",
        "pin_entered_caption": "Mã PIN vừa nhập:",
        "blood_type_label": "🩸 Nhóm máu (bắt buộc)",
        "blood_type_help": "Bắt buộc chọn để hồ sơ khẩn cấp (mã QR, hình nền màn hình khoá) luôn có "
                            "đủ thông tin khi cần cấp cứu.",
        "language_label": "🌐 Ngôn ngữ hiển thị",
        "enable_face_checkbox": "Thêm FaceID ngay bây giờ (tùy chọn)",
        "face_capture_label": "Chụp khuôn mặt",
        "register_button": "✅ ĐĂNG KÝ",
        "register_error_required": "❌ Vui lòng điền đầy đủ số điện thoại, họ tên và mã PIN.",
        "register_error_phone": "❌ Số điện thoại không hợp lệ (định dạng 10 số, bắt đầu bằng 0).",
        "register_error_pin": "❌ Mã PIN phải gồm đúng 4 chữ số.",
        "register_error_blood": "❌ Vui lòng chọn nhóm máu của bạn — đây là thông tin bắt buộc để hoàn "
                                 "tất đăng ký (phục vụ hồ sơ khẩn cấp).",
        "register_error_face_missing": "❌ Bạn đã bật FaceID nhưng chưa chụp ảnh. "
                                        "Vui lòng chụp ảnh hoặc bỏ chọn FaceID.",
        "register_error_duplicate_phone": "❌ Số điện thoại '{phone}' đã được đăng ký trước đó. "
                                           "Mỗi số điện thoại chỉ được tạo 1 tài khoản — vui lòng chuyển "
                                           "sang tab **Đăng nhập** hoặc dùng số điện thoại khác.",
        "register_initializing": "Đang khởi tạo tài khoản...",
        "register_warning_face_fail": "⚠️ Không xử lý được ảnh khuôn mặt, tài khoản sẽ được tạo "
                                       "không kèm FaceID. Bạn có thể thêm lại sau.",
        "register_warning_missing_cols": "⚠️ Bảng dữ liệu chưa có đủ cột lưu FaceID/nhóm máu/ngôn ngữ, "
                                          "nên tài khoản được tạo với các thông tin còn lại. Hãy chạy "
                                          "migration SQL thêm cột còn thiếu rồi cập nhật lại sau trong Cài đặt.",
        "register_success": "✅ Tạo tài khoản thành công!",
        "register_error_exists": "❌ Số điện thoại '{phone}' đã tồn tại. Vui lòng đăng nhập.",
        "register_error_db": "❌ Lỗi cơ sở dữ liệu:",

        # ---- Sidebar ----
        "sidebar_hello": "Xin chào",
        "sidebar_phone": "SĐT",
        "sidebar_blood": "🩸 Nhóm máu",
        "sidebar_adherence": "📊 Tỷ lệ tuân thủ",
        "sidebar_taken_today": "Đã uống hôm nay",
        "sidebar_no_schedule": "Chưa có lịch trình thuốc.",
        "sidebar_pending_invites": "👪 Bạn có {n} lời mời làm người thân đang chờ phê duyệt — "
                                    "xem ở tab **Cài đặt → Người thân**.",
        "sidebar_elderly_toggle": "🔎 Giao diện chữ to (dễ đọc)",
        "sidebar_logout": "🚪 Đăng xuất",

        # ---- Dashboard ----
        "dashboard_title": "💊 SafePill – Trung Tâm Quản Lý Dược Phẩm",
        "metric_med_count": "Số thuốc đang quản lý",
        "metric_interaction": "Tương tác thuốc",
        "metric_interaction_alert": "🚨 CÓ CẢNH BÁO",
        "metric_interaction_alert_delta": "Cần xem xét ngay",
        "metric_interaction_safe": "✅ An toàn",
        "metric_interaction_safe_delta": "Không phát hiện xung đột",
        "metric_schedule": "Lịch nhắc hôm nay",
        "metric_schedule_unit": "khung giờ",

        # ---- Tên tab ----
        "tab_home": "🏠 Hôm nay",
        "tab_ocr": "📷 Quét đơn thuốc",
        "tab_cabinet": "🗄️ Tủ thuốc số",
        "tab_matrix": "🔬 Tra cứu tương tác",
        "tab_expert": "🤖 Hỏi đáp AI",
        "tab_report": "📈 Báo cáo tuân thủ",
        "tab_qr": "🆘 QR khẩn cấp",
        "tab_settings": "⚙️ Cài đặt",

        # ---- Tab Hôm nay ----
        "home_header": "🏠 Lịch uống thuốc hôm nay",
        "home_auto_escalate_msg": "🚨 Đã quá {mins} phút kể từ giờ hẹn **{time}** mà **{drug}** vẫn chưa "
                                   "được xác nhận uống — SafePill đã tự động báo cho {n} người thân đang "
                                   "theo dõi bạn.",
        "home_auto_escalate_msg_no_family": "🚨 Đã quá {mins} phút kể từ giờ hẹn **{time}** mà **{drug}** "
                                     "vẫn chưa được xác nhận uống!",
        "home_custom_expander": "➕ Thêm / quản lý nhắc nhở thủ công",
        "home_custom_caption": "Đặt nhắc nhở tuỳ ý (đo huyết áp, tái khám, uống nước...) không cần gắn với "
                                "một loại thuốc cụ thể trong tủ thuốc.",
        "home_custom_label_input": "Nội dung nhắc nhở",
        "home_custom_label_placeholder": "VD: Đo huyết áp",
        "home_custom_time_input": "Giờ nhắc",
        "home_custom_add_btn": "➕ Thêm nhắc nhở",
        "home_custom_warn_empty": "⚠️ Vui lòng nhập nội dung nhắc nhở.",
        "home_custom_added": "✅ Đã thêm nhắc nhở thủ công.",
        "home_custom_list_title": "**Danh sách nhắc nhở thủ công:**",
        "home_custom_none": "Chưa có nhắc nhở thủ công nào.",
        "home_family_reminder_title": "**👪 Nhắc nhở từ người thân:**",
        "home_family_reminder_default_sender": "Người thân",
        "home_family_reminder_prefix": "nhắc bạn:",
        "home_empty": "Chưa có thuốc hoặc nhắc nhở nào. Hãy quét đơn thuốc hoặc thêm nhắc nhở thủ công ở trên.",
        "home_taken_checkbox": "Đã uống",
        "home_missed_btn": "❌ Bỏ lỡ",
        "home_missed_recorded": "⚠️ Đã ghi nhận bỏ lỡ liều **{drug}** ({n} lần liên tiếp).",
        "home_missed_escalated": "🚨 Đã tự động cảnh báo {n} người thân vì bỏ lỡ thuốc mức độ **{severity}** "
                                  "liên tiếp {streak} lần!",
        "home_low_stock": "📉 **{drug}** chỉ còn **{qty}** liều — hãy chuẩn bị mua thêm hoặc tái khám sớm!",
        "home_custom_today_title": "**Nhắc nhở thủ công hôm nay:**",
        "home_notification_caption": "🔔 Trình duyệt sẽ gửi thông báo kèm âm thanh nhắc nhở đúng giờ nếu "
                                      "bạn cho phép Notification và giữ tab này đang mở.",
        "home_conflict_warning": "⚠️ Tủ thuốc hiện có cảnh báo tương tác — xem chi tiết ở tab **Tủ thuốc số**.",
        "home_notification_title": "💊 SafePill nhắc nhở",
        "home_notification_body_suffix": "— đến giờ rồi!",
        "tts_read_aloud": "🔊 Đọc to",
        "tts_read_aloud_prefix": "Đến giờ uống",
        "tts_read_aloud_dose": "liều",
        "tts_read_aloud_at": "vào",

        # ---- Tab Quét đơn thuốc ----
        "ocr_header": "📷 Số hóa đơn thuốc bằng AI",
        "ocr_info": "Chụp ảnh trực tiếp, hoặc tải lên ảnh đơn thuốc/hồ sơ bệnh án đã có sẵn (viết tay, "
                    "vỉ thuốc, hoặc ảnh scan) — hệ thống sẽ tự động bóc tách tên thuốc, liều lượng và "
                    "thời điểm uống.",
        "ocr_clinic_section_title": "### 🏥 Thông tin nơi khám & cấp thuốc",
        "ocr_clinic_section_caption": "Điền thông tin của đơn thuốc này — sẽ tự động áp dụng cho mọi "
                                       "thuốc bạn quét bằng AI hoặc thêm thủ công bên dưới. Có thể để "
                                       "trống nếu không có.",
        "ocr_clinic_label": "Nơi khám bệnh",
        "ocr_clinic_placeholder": "VD: BV Chợ Rẫy",
        "ocr_doctor_label": "Bác sĩ điều trị",
        "ocr_doctor_placeholder": "VD: BS. Nguyễn Văn A",
        "ocr_pharmacy_label": "Nơi cấp thuốc",
        "ocr_pharmacy_placeholder": "VD: Nhà thuốc Long Châu",
        "ocr_method_label": "Bạn muốn thêm thuốc bằng cách nào?",
        "ocr_method_camera": "📷 Chụp ảnh trực tiếp bằng camera",
        "ocr_method_upload": "📁 Tải ảnh có sẵn lên (đơn thuốc / hồ sơ bệnh án đã chụp hoặc scan)",
        "ocr_method_manual": "✍️ Không có ảnh, tôi sẽ nhập thuốc thủ công",
        "ocr_camera_capture": "Chụp ảnh đơn thuốc / vỉ thuốc",
        "ocr_analyzing": "🤖 Đang phân tích hình ảnh bằng AI...",
        "ocr_no_meds_found": "⚠️ AI không nhận diện được thuốc nào trong ảnh này. Hãy thử chụp lại rõ "
                              "nét hơn, hoặc nhập tay ở khung bên dưới.",
        "ocr_added_success": "✅ Đã thêm {n} loại thuốc vào tủ thuốc!",
        "ocr_analyze_fail": "❌ Không thể phân tích ảnh:",
        "ocr_analyze_fail_hint": "Gợi ý: chụp ảnh rõ nét hơn, đủ sáng, hoặc chọn \"Không có ảnh, tôi sẽ "
                                  "nhập thuốc thủ công\" ở trên để nhập tay.",
        "ocr_manual_expander": "➕ Thêm thuốc thủ công (nếu AI không nhận diện được, hoặc muốn bổ sung thêm)",
        "ocr_upload_label": "Tải ảnh đơn thuốc / hồ sơ bệnh án (có thể chọn nhiều ảnh cùng lúc)",
        "ocr_upload_selected": "Đã chọn {n} ảnh. Xem trước bên dưới:",
        "ocr_analyze_all_btn": "🤖 Phân tích tất cả ảnh bằng AI",
        "ocr_analyzing_multi": "🤖 Đang phân tích {n} ảnh bằng AI...",
        "ocr_added_multi_success": "✅ Đã thêm {n} loại thuốc từ {files} ảnh vào tủ thuốc!",
        "ocr_failed_file": "❌ Không thể phân tích ảnh **{name}**:",
        "ocr_no_meds_multi": "⚠️ AI không nhận diện được thuốc nào trong các ảnh đã tải lên. Hãy thử "
                              "ảnh rõ nét hơn, hoặc nhập tay ở khung bên dưới.",
        "ocr_manual_only_success": "👍 Không sao cả! Bạn có thể bỏ qua bước chụp/tải ảnh và nhập trực "
                                    "tiếp thông tin thuốc ở khung bên dưới — vẫn đầy đủ tính năng nhắc "
                                    "nhở, cảnh báo tương tác như khi quét đơn.",
        "ocr_manual_title": "✍️ Nhập thuốc thủ công",
        "ocr_manual_name": "Tên thuốc",
        "ocr_manual_dose": "Liều lượng",
        "ocr_manual_time": "Thời điểm",
        "ocr_manual_type": "Loại/nhóm thuốc",
        "ocr_manual_color": "Màu sắc viên thuốc (tuỳ chọn)",
        "ocr_manual_color_placeholder": "VD: trắng, đỏ",
        "ocr_manual_shape": "Hình dạng (tuỳ chọn)",
        "ocr_manual_qty": "Số lượng còn lại (tuỳ chọn)",
        "ocr_manual_clinic_section": "**Thông tin nơi khám & cấp thuốc cho thuốc này**",
        "ocr_manual_submit": "Thêm vào tủ thuốc",
        "ocr_manual_added": "✅ Đã thêm thuốc.",
        "ocr_manual_warn_name": "Vui lòng nhập tên thuốc.",
        "time_morning": "Sáng", "time_noon": "Trưa", "time_afternoon": "Chiều", "time_evening": "Tối",
        "shape_round": "Tròn", "shape_oval": "Oval", "shape_tablet": "Viên nén",
        "shape_square": "Vuông", "shape_capsule": "Con nhộng",
        "ocr_manual_note": "Lời dặn / Ghi chú (uống trước/sau ăn, kiêng...)",
        "ocr_manual_note_placeholder": "VD: Uống sau khi ăn no",
        "cabinet_note_prefix": "📝 Lời dặn:",
        "sched_note": "Lời dặn / Ghi chú",
        "home_note_prefix": "📝",

        # ---- Tab Tủ thuốc số ----
        "cabinet_header": "🗄️ Tủ thuốc số & nhật ký tuân thủ",
        "cabinet_conflict_alert": "🚨 **CẢNH BÁO:** Phát hiện tương tác thuốc trong tủ thuốc hiện tại!",
        "cabinet_severity_label": "Mức độ",
        "cabinet_source_label": "Nguồn tham khảo",
        "cabinet_consult_warning": "⚠️ Vui lòng tham khảo ý kiến bác sĩ/dược sĩ trước khi tiếp tục phối "
                                    "hợp các thuốc trên.",
        "cabinet_food_warning_title": "🍽️ **Cảnh báo tương tác với thực phẩm/thảo dược phổ biến ở Việt Nam:**",
        "cabinet_food_warning_caption": "Cơ sở dữ liệu minh họa, chưa đầy đủ toàn bộ thuốc nam/TPCN trên thị trường.",
        "cabinet_empty": "Tủ thuốc trống. Hãy quét đơn thuốc hoặc thêm thuốc thủ công ở tab trước.",
        "cabinet_list_title": "📋 Danh mục thuốc hiện có",
        "cabinet_qty_unit": "liều",
        "cabinet_clinic_prefix": "🏥 Nơi khám:",
        "cabinet_doctor_prefix": "👨‍⚕️ BS điều trị:",
        "cabinet_pharmacy_prefix": "💊 Nơi cấp thuốc:",

        # ---- Tab Tra cứu tương tác ----
        "matrix_header": "🔬 Tra cứu & mô phỏng tương tác thuốc",
        "matrix_caption": "Kiểm tra nhanh 2 loại thuốc, hoặc 1 thuốc với thực phẩm/thảo dược (VD: rượu "
                           "bia, bưởi, thuốc nam...), trước khi phối hợp sử dụng.",
        "matrix_drug_a": "Thuốc A",
        "matrix_drug_b": "Thuốc B (hoặc thực phẩm/thảo dược)",
        "matrix_check_btn": "Kiểm tra tương tác",
        "matrix_drug_alert": "🚨 PHÁT HIỆN TƯƠNG TÁC THUỐC–THUỐC (Mức độ: {severity})",
        "matrix_drug_pair": "**Cặp thuốc:**",
        "matrix_effect": "**Hệ quả:**",
        "matrix_source": "**Nguồn tham khảo:**",
        "matrix_recommendation": "**Khuyến cáo:**",
        "matrix_recommendation_drug": "Không tự ý phối hợp, hỏi ý kiến bác sĩ/dược sĩ.",
        "matrix_recommendation_food": "Tránh phối hợp, hỏi ý kiến bác sĩ/dược sĩ nếu cần dùng chung.",
        "matrix_food_alert": "⚠️ PHÁT HIỆN TƯƠNG TÁC THUỐC–THỰC PHẨM/THẢO DƯỢC (Mức độ: {severity})",
        "matrix_safe": "✅ Chưa ghi nhận tương tác giữa `{a}` và `{b}` trong cơ sở dữ liệu hiện tại "
                        "(đã kiểm tra cả thuốc–thuốc và thuốc–thực phẩm/thảo dược).",
        "matrix_footer_caption": "Lưu ý: cơ sở dữ liệu minh họa chỉ bao gồm một số hoạt chất và thực "
                                  "phẩm/thảo dược phổ biến, không thay thế tra cứu dược thư chính thức.",
        

        # ---- Tab Hỏi đáp AI ----
        "expert_header": "🤖 Trợ lý hỏi đáp về thuốc & sức khỏe",
        "expert_grounding_caption": "🔎 Trợ lý được yêu cầu ưu tiên đối chiếu các nguồn uy tín (Drugs.com, "
                                     "Dược thư Quốc gia Việt Nam, MedlinePlus, các bệnh viện lớn...) và "
                                     "đính kèm liên kết nguồn ở cuối câu trả lời khi tìm được, giúp bạn "
                                     "tự kiểm chứng lại thông tin.",
        "expert_chat_placeholder": "Hỏi về liều lượng, tác dụng phụ, triệu chứng...",
        "expert_analyzing": "Đang phân tích...",
        "expert_sources_title": "\n\n**Nguồn tham khảo:**\n",
        "expert_error": "Lỗi kết nối AI:",
        "expert_anon_name": "Ẩn danh",
        "expert_lang_instruction": "Hãy trả lời ngắn gọn, chính xác, dễ hiểu bằng tiếng Việt.",

        # ---- Tab Báo cáo tuân thủ ----
        "report_header": "📈 Báo cáo tuân thủ điều trị",
        "report_caption": "Theo dõi tỷ lệ tuân thủ theo ngày và xuất báo cáo để mang đi khám bệnh.",
        "report_today_rate": "Tỷ lệ tuân thủ hôm nay",
        "report_save_btn": "💾 Lưu tuân thủ hôm nay vào lịch sử",
        "report_no_schedule_warn": "⚠️ Chưa có lịch thuốc hôm nay để lưu.",
        "report_save_success": "✅ Đã lưu snapshot tuân thủ hôm nay.",
        "report_chart_title": "📉 Biểu đồ tuân thủ theo thời gian",
        "report_no_history": "ℹ️ Chưa có dữ liệu lịch sử. Hãy bấm nút 'Lưu tuân thủ hôm nay vào lịch sử' "
                              "mỗi ngày để bắt đầu tích luỹ dữ liệu cho biểu đồ.",
        "report_no_matplotlib": "⚠️ Thư viện matplotlib chưa được cài đặt trên máy chủ. Hãy thêm "
                                 "'matplotlib' vào requirements.txt để hiển thị biểu đồ.",
        "report_chart_ylabel": "Tỷ lệ tuân thủ (%)",
        "report_chart_xlabel": "Ngày",
        "report_chart_title_prefix": "Tuân thủ điều trị —",
        "report_download_pdf": "📄 Tải báo cáo PDF",
        "report_download_png": "🖼️ Tải ảnh PNG",
        "report_bring_to_doctor": "💡 Mang file PDF/ảnh này đi khám để bác sĩ nắm được mức độ tuân thủ điều trị của bạn.",

        # ---- Tab QR khẩn cấp ----
        "qr_header": "🆘 Thẻ QR khẩn cấp",
        "qr_info": "ℹ️ Mã QR này chứa danh sách thuốc đang dùng, cảnh báo tương tác và số điện thoại "
                   "người thân. In và dán lên ví hoặc tủ thuốc — khi gặp cấp cứu, người xung quanh hoặc "
                   "nhân viên y tế chỉ cần quét mã là biết ngay bạn đang dùng thuốc gì.",
        "qr_no_library": "⚠️ Thư viện 'qrcode' chưa được cài đặt trên máy chủ. Hãy thêm 'qrcode[pil]' "
                          "vào requirements.txt để bật tính năng này.",
        "qr_image_caption": "Quét mã để xem thông tin khẩn cấp",
        "qr_download_btn": "⬇️ Tải mã QR (PNG)",
        "qr_content_title": "**Nội dung được mã hoá trong QR:**",
        "qr_wallpaper_title": "🔒 Đặt làm hình nền màn hình khoá",
        "qr_wallpaper_info": "💡 Rất khuyến khích: đặt ảnh này làm **hình nền màn hình khoá (Lock "
                              "Screen)** của điện thoại. Nhờ vậy, khi máy đang khoá và bạn không tỉnh "
                              "táo để mở khoá, người sơ cứu hoặc nhân viên y tế vẫn nhìn thấy và quét "
                              "được mã QR ngay trên màn hình khoá mà **không cần mật khẩu**.",
        "qr_size_select": "Chọn kích thước theo loại máy",
        "qr_wallpaper_preview_caption": "Xem trước hình nền",
        "qr_wallpaper_download": "⬇️ Tải hình nền màn hình khoá",
        "qr_wallpaper_howto_title": "**Cách đặt làm hình nền màn hình khoá:**\n\n"
                                     "- **iPhone:** Tải ảnh → mở app *Ảnh* → chọn ảnh vừa tải → bấm nút "
                                     "Chia sẻ → *Dùng làm hình nền* → chọn **Màn hình khoá** (Lock "
                                     "Screen) → Xong.\n"
                                     "- **Android:** Tải ảnh → mở ảnh trong *Thư viện* → chạm menu ⋮ → "
                                     "*Đặt làm hình nền* → chọn **Màn hình khoá**.\n\n"
                                     "⚠️ Lưu ý: một số dòng máy có Face ID/vân tay hoặc widget đồng hồ "
                                     "có thể che một phần hình — hãy tự kiểm tra lại màn hình khoá sau "
                                     "khi đặt để đảm bảo mã QR không bị che.",
        "qr_footer_caption": "ℹ️ Lưu ý: mã QR chỉ chứa thông tin bạn tự khai báo trong SafePill, không "
                              "thay thế hồ sơ bệnh án chính thức. Hãy cập nhật lại mã mỗi khi thay đổi thuốc.",

        # ---- Tab Cài đặt ----
        "settings_header": "⚙️ Cài đặt",
        "settings_sub_account": "👤 Tài khoản",
        "settings_sub_schedule": "⏰ Lịch uống thuốc",
        "settings_sub_notification": "🔔 Thông báo & Âm thanh",
        "settings_sub_family": "👪 Người thân",
        "notif_enable_btn": "🔔 Bật thông báo & âm thanh (bấm 1 lần)",
        "notif_permission_granted": "✅ Đã bật thông báo thành công!",
        "notif_permission_denied": "❌ Trình duyệt đã từ chối quyền thông báo. Vào Cài đặt trình duyệt/điện thoại → bật lại quyền Thông báo cho trang này.",
        "notif_not_supported": "⚠️ Trình duyệt này không hỗ trợ thông báo đẩy.",
        "notif_ios_warning": "⚠️ iPhone/iPad (Safari) không hỗ trợ thông báo đẩy trên trình duyệt thường. Hãy thêm SafePill vào Màn hình chính, và luôn để ý banner cảnh báo màu đỏ/vàng ngay trong ứng dụng — đây là kênh cảnh báo đáng tin cậy nhất trên iPhone.",
        "notif_ios_add_home_title": "📱 iPhone/iPad: hãy thêm SafePill vào Màn hình chính để nhận cảnh báo tốt nhất",
        "notif_ios_add_home_step1": "1️⃣ Bấm biểu tượng Chia sẻ (hình vuông có mũi tên) ở thanh dưới (Safari)",
        "notif_ios_add_home_step2": "2️⃣ Chọn \"Thêm vào MH chính\" (Add to Home Screen)",
        "notif_ios_add_home_step3": "3️⃣ Bấm \"Thêm\", rồi luôn mở SafePill từ icon trên Màn hình chính (không mở qua Safari)",
        "notif_ios_add_home_note": "Lưu ý: kể cả sau khi thêm vào Màn hình chính, SafePill chỉ nhắc được khi app đang mở. Hãy chủ động mở app vào các giờ uống thuốc và theo dõi banner đỏ/vàng trong ứng dụng.",
        "acc_personal_info": "Thông tin cá nhân",
        "acc_full_name": "Họ và tên",
        "acc_blood_type": "🩸 Nhóm máu",
        "acc_language": "🌐 Ngôn ngữ hiển thị",
        "acc_save_btn": "Lưu thông tin",
        "acc_error_empty_name": "❌ Họ và tên không được để trống.",
        "acc_missing_col_warn": "⚠️ Bảng dữ liệu chưa có cột 'blood_type'/'language'. Hãy chạy migration "
                                 "SQL thêm cột này để lưu đầy đủ.",
        "acc_update_success": "✅ Đã cập nhật thông tin cá nhân.",
        "acc_update_error": "Lỗi cập nhật:",
        "acc_change_pin": "Đổi mã PIN",
        "acc_current_pin": "Mã PIN hiện tại",
        "acc_new_pin": "Mã PIN mới",
        "acc_confirm_pin": "Xác nhận mã PIN mới",
        "acc_change_pin_btn": "Đổi PIN",
        "acc_pin_error_empty": "❌ Vui lòng điền đầy đủ cả 3 trường.",
        "acc_pin_error_wrong": "❌ Mã PIN hiện tại không đúng.",
        "acc_pin_error_format": "❌ Mã PIN mới phải gồm đúng 4 chữ số.",
        "acc_pin_error_mismatch": "❌ Xác nhận mã PIN mới không khớp.",
        "acc_pin_success": "✅ Đã đổi mã PIN thành công.",
        "acc_faceid_title": "FaceID",
        "acc_faceid_registered": "✅ Tài khoản đã đăng ký FaceID.",
        "acc_faceid_not_registered": "ℹ️ Tài khoản chưa đăng ký FaceID.",
        "acc_faceid_expander": "📷 Chụp lại / đăng ký FaceID mới",
        "acc_faceid_capture": "Chụp khuôn mặt",
        "acc_faceid_save_btn": "Lưu FaceID",
        "acc_faceid_bad_image": "❌ Không xử lý được ảnh, vui lòng thử lại.",
        "acc_faceid_saved": "✅ Đã lưu FaceID mới.",
        "acc_faceid_save_error": "❌ Không thể lưu FaceID (kiểm tra đã chạy migration thêm cột "
                                  "face_data/face_hash chưa):",
        "acc_faceid_remove_btn": "🗑️ Xoá FaceID",
        "acc_faceid_removed": "✅ Đã xoá FaceID khỏi tài khoản.",
        "acc_faceid_remove_error": "Lỗi xoá FaceID:",

        "sched_title": "Chỉnh giờ nhắc & liều lượng từng loại thuốc",
        "sched_empty": "Chưa có thuốc nào trong tủ thuốc để đặt lịch. Hãy quét đơn hoặc thêm thuốc thủ công.",
        "sched_med_fallback": "Thuốc #{n}",
        "sched_dose": "Liều lượng",
        "sched_time": "Giờ nhắc chính xác",
        "sched_color": "Màu sắc viên thuốc",
        "sched_shape": "Hình dạng",
        "sched_qty": "Số lượng còn lại",
        "sched_clinic": "Nơi khám bệnh",
        "sched_doctor": "Bác sĩ điều trị",
        "sched_pharmacy": "Nơi cấp thuốc",
        "sched_save_btn": "Lưu thay đổi",
        "sched_save_success": "✅ Đã cập nhật lịch nhắc cho {med}.",
        "sched_footer_caption": "💡 Lịch nhắc & thông tin nơi khám/bác sĩ/nơi cấp thuốc được lưu bền lên "
                                 "Supabase (cột 'diagnostic'), sẽ không mất khi tải lại trang hoặc đăng "
                                 "nhập lại.",

        "notif_title": "Tuỳ chỉnh thông báo & âm thanh nhắc nhở",
        "notif_caption": "Âm thanh sẽ phát cùng lúc với thông báo trên trình duyệt điện thoại/máy tính "
                          "khi đến giờ nhắc uống thuốc hoặc nhắc nhở thủ công. Cần cho phép quyền "
                          "Notification và giữ tab SafePill đang mở (hoặc chạy nền) để nhận được nhắc nhở.",
        "notif_sound_type": "Loại âm thanh nhắc nhở",
        "notif_sound_beep": "🔔 Beep (mặc định)",
        "notif_sound_chime": "🎐 Chime (chuông nhẹ)",
        "notif_sound_bell": "🔔 Bell (chuông lớn)",
        "notif_volume": "Âm lượng",
        "notif_saved": "✅ Đã lưu cài đặt âm thanh nhắc nhở.",
        "notif_test_title": "**Nghe thử âm thanh:**",
        "notif_test_btn": "▶ Nghe thử",
        "notif_tip_caption": "💡 Mẹo: trên điện thoại, hãy thêm SafePill vào màn hình chính (Add to Home "
                              "Screen) và cho phép quyền Thông báo trong trình duyệt để nhận nhắc nhở ổn định hơn.",
        "notif_tts_title": "🔊 Đọc to bằng giọng nói (Text-to-Speech)",
        "notif_tts_toggle": "Hiện nút 🔊 đọc to tên thuốc/liều lượng ở tab Hôm nay",
        "notif_tts_caption": "👴 Dành cho người già không quen thao tác chữ nhỏ: bấm nút 🔊 cạnh mỗi "
                              "thuốc để nghe đọc to tên thuốc, liều lượng và thời điểm uống bằng giọng "
                              "tiếng Việt của trình duyệt.",

        "family_title": "👪 Người thân nhắc nhở tôi",
        "family_caption": "Mời một người thân (đã có tài khoản SafePill) để họ có thể gửi nhắc nhở trực "
                           "tiếp đến bạn — ví dụ: \"Con nhắc mẹ uống thuốc huyết áp nhé!\". Người thân "
                           "cần đăng nhập bằng chính số điện thoại của họ và chấp nhận lời mời trước khi "
                           "gửi được nhắc nhở.",
        "family_invite_phone": "SĐT người thân",
        "family_invite_name": "Tên gợi nhớ (tuỳ chọn)",
        "family_invite_name_placeholder": "VD: Con trai",
        "family_invite_btn": "📨 Gửi lời mời",
        "family_invite_error_phone": "❌ Số điện thoại không hợp lệ.",
        "family_invite_error_self": "❌ Không thể tự mời chính mình.",
        "family_invite_sent": "✅ Đã gửi lời mời đến {phone}.",
        "family_list_title": "**Danh sách người thân:**",
        "family_status_pending": "⏳ Đang chờ",
        "family_status_accepted": "✅ Đã chấp nhận",
        "family_status_declined": "❌ Đã từ chối",
        "family_none": "Chưa mời người thân nào.",
        "family_delete_error": "❌ Không xoá được liên kết:",
        "family_pending_title": "📥 Lời mời đang chờ tôi phê duyệt",
        "family_owner_label": "Chủ tủ thuốc:",
        "family_accept_btn": "✅ Chấp nhận",
        "family_accept_success": "✅ Đã chấp nhận làm người thân theo dõi.",
        "family_accept_error": "❌ Không cập nhật được trạng thái lời mời. Nguyên nhân thường gặp: bảng "
                                "'safepill_family_links' chưa có RLS policy cho phép UPDATE với vai trò "
                                "anon. Chi tiết lỗi:",
        "family_decline_btn": "❌ Từ chối",
        "family_decline_error": "❌ Không cập nhật được trạng thái lời mời:",
        "family_no_pending": "Không có lời mời nào đang chờ.",
        "family_send_title": "📤 Gửi nhắc nhở cho người thân tôi đang theo dõi",
        "family_send_none": "Bạn chưa được ai chấp nhận cho vai trò người thân. Khi có người mời và bạn "
                             "chấp nhận ở mục trên, họ sẽ xuất hiện tại đây để bạn gửi nhắc nhở.",
        "family_send_mode": "Thời điểm gửi",
        "family_send_now": "Gửi ngay",
        "family_send_scheduled": "Đặt giờ cụ thể",
        "family_send_pick_time": "Chọn giờ và phút muốn gửi nhắc nhở:",
        "family_send_hour": "Giờ",
        "family_send_minute": "Phút",
        "family_send_target": "Gửi nhắc nhở cho",
        "family_send_msg": "Nội dung nhắc nhở",
        "family_send_msg_placeholder": "VD: Nhớ uống thuốc huyết áp buổi tối nhé!",
        "family_send_btn": "📨 Gửi nhắc nhở",
        "family_send_warn_empty": "⚠️ Vui lòng nhập nội dung nhắc nhở.",
        "family_send_success": "✅ Đã gửi nhắc nhở! Người nhận sẽ thấy thông báo kèm âm thanh khi mở/đang "
                                "mở SafePill (đúng giờ nếu bạn đặt lịch).",
        "family_send_error": "Lỗi:",
        "family_footer_caption": "ℹ️ Lưu ý: nhắc nhở từ người thân chỉ hiển thị và phát âm thanh khi "
                                  "người nhận đang mở hoặc tải lại trang SafePill (chưa có push "
                                  "notification nền thật sự khi tắt trình duyệt).",
    },

    "en": {
        # ---- Onboarding ----
        "app_title": "💊 SafePill",
        "app_tagline": "Smart medication assistant — scan prescriptions, detect dangerous interactions, "
                        "and get reminded to take your medicine on time.",
        "onboarding_card_title": "Digital Healthcare Solution",
        "onboarding_card_desc": "Scan prescriptions with your camera, automatically detect dangerous "
                                 "drug interactions, and get reminded to take your medicine every day.",
        "start_button": "GET STARTED ➔",
        "disclaimer": ("⚠️ SafePill is a medication reminder and lookup assistant, "
                        "NOT a substitute for a doctor's or pharmacist's diagnosis. "
                        "In an emergency, please contact the nearest medical facility."),

        # ---- Sign in / Sign up ----
        "auth_header": "🔐 Sign In / Sign Up",
        "tab_login": "🔑 Sign In",
        "tab_register": "🆕 Quick Sign Up (5 taps)",
        "login_method_label": "Unlock with:",
        "login_pin": "4-digit PIN",
        "login_face": "Face (FaceID)",
        "phone_label": "Phone number",
        "phone_placeholder": "0XXXXXXXXX",
        "pin_label": "PIN (4 digits)",
        "login_button": "Sign In",
        "login_warning_empty": "⚠️ Please enter both your phone number and PIN.",
        "login_authenticating": "Authenticating...",
        "login_success": "✅ Signed in successfully!",
        "login_wrong_pin": "❌ Incorrect PIN.",
        "login_phone_not_found": "❌ This phone number is not registered.",
        "login_db_error": "Database connection error:",
        "face_login_hint": "📷 Look straight at the camera to match your registered face.",
        "face_login_capture": "Take a photo to verify",
        "face_login_matching": "🔍 Matching biometric data...",
        "face_login_bad_image": "❌ Could not process the photo. Please try again with a clearer image.",
        "face_login_missing_col": "⚠️ The database is missing the FaceID columns (face_data/face_hash). "
                                   "Please run the SQL migration to add these columns before using FaceID.",
        "face_login_no_accounts": "⚠️ No accounts have registered FaceID yet. "
                                   "Please sign in with your PIN, then enable FaceID during registration.",
        "face_login_welcome": "✅ FaceID verified! Welcome",
        "face_login_profile_fail": "❌ Could not load the user profile, please try again.",
        "face_login_no_match": "❌ No matching face found in the system. "
                                "Please sign in with your PIN or create a new account.",
        "face_login_error": "FaceID authentication error:",

        "register_caption": "Fill in all 4 required fields (phone, full name, PIN, blood type) — FaceID "
                             "remains optional, you can enable it now or add it later.",
        "full_name_label": "👤 Full name",
        "full_name_placeholder": "John Doe",
        "pin_create_label": "🔢 Create a PIN (4 digits)",
        "pin_show_checkbox": "Show",
        "pin_show_help": "Show the PIN to double-check it, no need to re-type it (fewer taps)",
        "pin_entered_caption": "PIN entered:",
        "blood_type_label": "🩸 Blood type (required)",
        "blood_type_help": "Required so your emergency profile (QR code, lock screen wallpaper) always "
                            "has complete information in an emergency.",
        "language_label": "🌐 Display language",
        "enable_face_checkbox": "Add FaceID now (optional)",
        "face_capture_label": "Take a photo of your face",
        "register_button": "✅ SIGN UP",
        "register_error_required": "❌ Please fill in your phone number, full name, and PIN.",
        "register_error_phone": "❌ Invalid phone number (10 digits, starting with 0).",
        "register_error_pin": "❌ PIN must be exactly 4 digits.",
        "register_error_blood": "❌ Please select your blood type — this is required to complete "
                                 "registration (used for your emergency profile).",
        "register_error_face_missing": "❌ You enabled FaceID but haven't taken a photo yet. Please take "
                                        "a photo or disable FaceID.",
        "register_error_duplicate_phone": "❌ The phone number '{phone}' is already registered. Each "
                                           "phone number can only create one account — please switch to "
                                           "the **Sign In** tab or use a different number.",
        "register_initializing": "Creating your account...",
        "register_warning_face_fail": "⚠️ Could not process the face photo, the account will be created "
                                       "without FaceID. You can add it again later.",
        "register_warning_missing_cols": "⚠️ The database is missing some columns (FaceID/blood "
                                          "type/language), so the account was created with the remaining "
                                          "information. Please run the SQL migration to add the missing "
                                          "columns, then update them later in Settings.",
        "register_success": "✅ Account created successfully!",
        "register_error_exists": "❌ The phone number '{phone}' already exists. Please sign in instead.",
        "register_error_db": "❌ Database error:",

        # ---- Sidebar ----
        "sidebar_hello": "Hello",
        "sidebar_phone": "Phone",
        "sidebar_blood": "🩸 Blood type",
        "sidebar_adherence": "📊 Adherence rate",
        "sidebar_taken_today": "Taken today",
        "sidebar_no_schedule": "No medication schedule yet.",
        "sidebar_pending_invites": "👪 You have {n} pending family invite(s) — "
                                    "see **Settings → Family** tab.",
        "sidebar_elderly_toggle": "🔎 Large text mode (easier to read)",
        "sidebar_logout": "🚪 Log out",

        # ---- Dashboard ----
        "dashboard_title": "💊 SafePill – Medication Management Center",
        "metric_med_count": "Medications managed",
        "metric_interaction": "Drug interactions",
        "metric_interaction_alert": "🚨 WARNING",
        "metric_interaction_alert_delta": "Needs review now",
        "metric_interaction_safe": "✅ Safe",
        "metric_interaction_safe_delta": "No conflicts detected",
        "metric_schedule": "Today's schedule",
        "metric_schedule_unit": "time slot(s)",

        # ---- Tab names ----
        "tab_home": "🏠 Today",
        "tab_ocr": "📷 Scan Prescription",
        "tab_cabinet": "🗄️ Digital Cabinet",
        "tab_matrix": "🔬 Interaction Lookup",
        "tab_expert": "🤖 AI Q&A",
        "tab_report": "📈 Adherence Report",
        "tab_qr": "🆘 Emergency QR",
        "tab_settings": "⚙️ Settings",

        # ---- Today tab ----
        "home_header": "🏠 Today's medication schedule",
        "home_auto_escalate_msg": "🚨 It's been over {mins} minutes since **{time}** and **{drug}** is "
                                   "still not marked as taken — SafePill has automatically notified {n} "
                                   "family member(s) who follow you.",
        "home_auto_escalate_msg_no_family": "🚨 It's been over {mins} minutes since **{time}** and **{drug}** "
                                     "is still not marked as taken!",
        "home_custom_expander": "➕ Add / manage custom reminders",
        "home_custom_caption": "Set any reminder you like (blood pressure check, follow-up visit, drink "
                                "water...) without linking it to a specific medication.",
        "home_custom_label_input": "Reminder content",
        "home_custom_label_placeholder": "E.g. Check blood pressure",
        "home_custom_time_input": "Reminder time",
        "home_custom_add_btn": "➕ Add reminder",
        "home_custom_warn_empty": "⚠️ Please enter the reminder content.",
        "home_custom_added": "✅ Custom reminder added.",
        "home_custom_list_title": "**List of custom reminders:**",
        "home_custom_none": "No custom reminders yet.",
        "home_family_reminder_title": "**👪 Reminders from family:**",
        "home_family_reminder_default_sender": "Family member",
        "home_family_reminder_prefix": "reminds you:",
        "home_empty": "No medications or reminders yet. Scan a prescription or add a custom reminder above.",
        "home_taken_checkbox": "Taken",
        "home_missed_btn": "❌ Missed",
        "home_missed_recorded": "⚠️ Missed dose recorded for **{drug}** ({n} times in a row).",
        "home_missed_escalated": "🚨 Automatically alerted {n} family member(s) due to {streak} "
                                  "consecutive missed doses of a **{severity}** severity medication!",
        "home_low_stock": "📉 **{drug}** has only **{qty}** doses left — consider restocking or booking "
                           "a follow-up soon!",
        "home_custom_today_title": "**Today's custom reminders:**",
        "home_notification_caption": "🔔 Your browser will send a notification with sound at the right "
                                      "time if you allow notifications and keep this tab open.",
        "home_conflict_warning": "⚠️ There are active interaction warnings — see the **Digital Cabinet** tab for details.",
        "home_notification_title": "💊 SafePill reminder",
        "home_notification_body_suffix": "— it's time!",
        "tts_read_aloud": "🔊 Read aloud",
        "tts_read_aloud_prefix": "Time to take",
        "tts_read_aloud_dose": "dose",
        "tts_read_aloud_at": "at",

        # ---- Scan Prescription tab ----
        "ocr_header": "📷 Digitize your prescription with AI",
        "ocr_info": "Take a photo directly, or upload an existing prescription/medical record image "
                    "(handwritten, pill blister, or scan) — the system will automatically extract the "
                    "medication name, dosage, and time to take it.",
        "ocr_clinic_section_title": "### 🏥 Clinic & pharmacy information",
        "ocr_clinic_section_caption": "Fill in this prescription's details — it will automatically apply "
                                       "to every medication you scan with AI or add manually below. Leave "
                                       "blank if not applicable.",
        "ocr_clinic_label": "Clinic / hospital",
        "ocr_clinic_placeholder": "E.g. City General Hospital",
        "ocr_doctor_label": "Treating physician",
        "ocr_doctor_placeholder": "E.g. Dr. Jane Smith",
        "ocr_pharmacy_label": "Pharmacy",
        "ocr_pharmacy_placeholder": "E.g. Main Street Pharmacy",
        "ocr_method_label": "How would you like to add your medication?",
        "ocr_method_camera": "📷 Take a photo directly with the camera",
        "ocr_method_upload": "📁 Upload an existing image (prescription / medical record photo or scan)",
        "ocr_method_manual": "✍️ No image available, I'll enter medications manually",
        "ocr_camera_capture": "Photograph the prescription / pill blister",
        "ocr_analyzing": "🤖 Analyzing the image with AI...",
        "ocr_no_meds_found": "⚠️ AI could not identify any medication in this image. Try a clearer photo, "
                              "or enter it manually below.",
        "ocr_added_success": "✅ Added {n} medication(s) to your cabinet!",
        "ocr_analyze_fail": "❌ Could not analyze the image:",
        "ocr_analyze_fail_hint": "Tip: take a clearer, well-lit photo, or choose \"No image available, "
                                  "I'll enter medications manually\" above to enter it by hand.",
        "ocr_manual_expander": "➕ Add medication manually (if AI couldn't recognize it, or to add more)",
        "ocr_upload_label": "Upload prescription / medical record images (multiple images allowed)",
        "ocr_upload_selected": "{n} image(s) selected. Preview below:",
        "ocr_analyze_all_btn": "🤖 Analyze all images with AI",
        "ocr_analyzing_multi": "🤖 Analyzing {n} image(s) with AI...",
        "ocr_added_multi_success": "✅ Added {n} medication(s) from {files} image(s) to your cabinet!",
        "ocr_failed_file": "❌ Could not analyze image **{name}**:",
        "ocr_no_meds_multi": "⚠️ AI could not identify any medications in the uploaded images. Try "
                              "clearer images, or enter them manually below.",
        "ocr_manual_only_success": "👍 No problem! You can skip the photo step and enter your medication "
                                    "information directly below — you'll still get full reminder and "
                                    "interaction-warning features, just like scanning a prescription.",
        "ocr_manual_title": "✍️ Enter medication manually",
        "ocr_manual_name": "Medication name",
        "ocr_manual_dose": "Dosage",
        "ocr_manual_time": "Time of day",
        "ocr_manual_type": "Drug class / type",
        "ocr_manual_color": "Pill color (optional)",
        "ocr_manual_color_placeholder": "E.g. white, red",
        "ocr_manual_shape": "Shape (optional)",
        "ocr_manual_qty": "Quantity remaining (optional)",
        "ocr_manual_clinic_section": "**Clinic & pharmacy info for this medication**",
        "ocr_manual_submit": "Add to cabinet",
        "ocr_manual_added": "✅ Medication added.",
        "ocr_manual_warn_name": "Please enter the medication name.",
        "time_morning": "Morning", "time_noon": "Noon", "time_afternoon": "Afternoon", "time_evening": "Evening",
        "shape_round": "Round", "shape_oval": "Oval", "shape_tablet": "Tablet",
        "shape_square": "Square", "shape_capsule": "Capsule",
        "ocr_manual_note": "Instructions / Notes (drink before/after meals, avoid certain foods...)",  
        "ocr_manual_note_placeholder": "e.g., Drink after a full meal",  
        "cabinet_note_prefix": "📝 Instructions:",  
        "sched_note": "Instructions / Notes",  
        "home_note_prefix": "📝",

        # ---- Digital Cabinet tab ----
        "cabinet_header": "🗄️ Digital medicine cabinet & adherence log",
        "cabinet_conflict_alert": "🚨 **WARNING:** Drug interactions detected in your current cabinet!",
        "cabinet_severity_label": "Severity",
        "cabinet_source_label": "Reference source",
        "cabinet_consult_warning": "⚠️ Please consult your doctor or pharmacist before continuing to "
                                    "combine the medications above.",
        "cabinet_food_warning_title": "🍽️ **Warnings for common food/herbal interactions in Vietnam:**",
        "cabinet_food_warning_caption": "Illustrative database only, not an exhaustive list of all "
                                         "traditional remedies/supplements on the market.",
        "cabinet_empty": "Your cabinet is empty. Scan a prescription or add a medication manually in the previous tab.",
        "cabinet_list_title": "📋 Current medication list",
        "cabinet_qty_unit": "dose(s)",
        "cabinet_clinic_prefix": "🏥 Clinic:",
        "cabinet_doctor_prefix": "👨‍⚕️ Physician:",
        "cabinet_pharmacy_prefix": "💊 Pharmacy:",

        # ---- Interaction Lookup tab ----
        "matrix_header": "🔬 Interaction lookup & simulator",
        "matrix_caption": "Quickly check two medications, or one medication against a food/herbal item "
                           "(e.g. alcohol, grapefruit, traditional remedies...) before combining them.",
        "matrix_drug_a": "Medication A",
        "matrix_drug_b": "Medication B (or food/herbal item)",
        "matrix_check_btn": "Check interaction",
        "matrix_drug_alert": "🚨 DRUG–DRUG INTERACTION DETECTED (Severity: {severity})",
        "matrix_drug_pair": "**Medication pair:**",
        "matrix_effect": "**Effect:**",
        "matrix_source": "**Reference source:**",
        "matrix_recommendation": "**Recommendation:**",
        "matrix_recommendation_drug": "Do not combine on your own — consult a doctor or pharmacist.",
        "matrix_recommendation_food": "Avoid combining — consult a doctor or pharmacist if needed together.",
        "matrix_food_alert": "⚠️ DRUG–FOOD/HERBAL INTERACTION DETECTED (Severity: {severity})",
        "matrix_safe": "✅ No interaction found between `{a}` and `{b}` in the current database (both "
                        "drug–drug and drug–food/herbal interactions were checked).",
        "matrix_footer_caption": "Note: this illustrative database only covers some common active "
                                  "ingredients and foods/herbs, and does not replace an official pharmacopeia lookup.",
        
        # ---- AI Q&A tab ----
        "expert_header": "🤖 Medication & health Q&A assistant",
        "expert_grounding_caption": "🔎 The assistant is instructed to prioritize reputable sources "
                                     "(Drugs.com, national pharmacopeias, MedlinePlus, major hospitals...) "
                                     "and attach source links at the end of its answer when found, so you "
                                     "can verify the information yourself.",
        "expert_chat_placeholder": "Ask about dosage, side effects, symptoms...",
        "expert_analyzing": "Analyzing...",
        "expert_sources_title": "\n\n**Sources:**\n",
        "expert_error": "AI connection error:",
        "expert_anon_name": "Anonymous",
        "expert_lang_instruction": "Please answer concisely, accurately, and clearly in English.",

        # ---- Adherence Report tab ----
        "report_header": "📈 Treatment adherence report",
        "report_caption": "Track your daily adherence rate and export a report to bring to your doctor.",
        "report_today_rate": "Today's adherence rate",
        "report_save_btn": "💾 Save today's adherence to history",
        "report_no_schedule_warn": "⚠️ No medication schedule today to save.",
        "report_save_success": "✅ Today's adherence snapshot saved.",
        "report_chart_title": "📉 Adherence trend chart",
        "report_no_history": "ℹ️ No history data yet. Tap 'Save today's adherence to history' every day "
                              "to start building the chart.",
        "report_no_matplotlib": "⚠️ The matplotlib library is not installed on the server. Add "
                                 "'matplotlib' to requirements.txt to display the chart.",
        "report_chart_ylabel": "Adherence rate (%)",
        "report_chart_xlabel": "Date",
        "report_chart_title_prefix": "Treatment adherence —",
        "report_download_pdf": "📄 Download PDF report",
        "report_download_png": "🖼️ Download PNG image",
        "report_bring_to_doctor": "💡 Bring this PDF/image file to your appointment so your doctor can see your adherence level.",

        # ---- Emergency QR tab ----
        "qr_header": "🆘 Emergency QR card",
        "qr_info": "ℹ️ This QR code contains your current medications, interaction warnings, and family "
                   "contact numbers. Print it and attach it to your wallet or medicine cabinet — in an "
                   "emergency, anyone nearby or medical staff can scan it to instantly know what you're taking.",
        "qr_no_library": "⚠️ The 'qrcode' library is not installed on the server. Add 'qrcode[pil]' to "
                          "requirements.txt to enable this feature.",
        "qr_image_caption": "Scan to view emergency information",
        "qr_download_btn": "⬇️ Download QR code (PNG)",
        "qr_content_title": "**Content encoded in the QR code:**",
        "qr_wallpaper_title": "🔒 Set as lock screen wallpaper",
        "qr_wallpaper_info": "💡 Highly recommended: set this image as your phone's **lock screen "
                              "wallpaper**. That way, if your phone is locked and you're unable to unlock "
                              "it, first responders or medical staff can still see and scan the QR code "
                              "right from the lock screen **without needing your passcode**.",
        "qr_size_select": "Choose a size for your device",
        "qr_wallpaper_preview_caption": "Wallpaper preview",
        "qr_wallpaper_download": "⬇️ Download lock screen wallpaper",
        "qr_wallpaper_howto_title": "**How to set it as your lock screen wallpaper:**\n\n"
                                     "- **iPhone:** Download the image → open the *Photos* app → select "
                                     "it → tap Share → *Use as Wallpaper* → choose **Lock Screen** → Done.\n"
                                     "- **Android:** Download the image → open it in your *Gallery* → tap "
                                     "the ⋮ menu → *Set as wallpaper* → choose **Lock screen**.\n\n"
                                     "⚠️ Note: Face ID/fingerprint sensors or clock widgets on some "
                                     "devices may cover part of the image — please check your lock screen "
                                     "afterward to make sure the QR code isn't obscured.",
        "qr_footer_caption": "ℹ️ Note: the QR code only contains information you entered in SafePill, and "
                              "does not replace an official medical record. Update it whenever your medications change.",

        # ---- Settings tab ----
        "settings_header": "⚙️ Settings",
        "settings_sub_account": "👤 Account",
        "settings_sub_schedule": "⏰ Medication schedule",
        "settings_sub_notification": "🔔 Notifications & sound",
        "settings_sub_family": "👪 Family",
        "notif_enable_btn": "🔔 Enable notifications & sound (tap once)",
        "notif_permission_granted": "✅ Notifications enabled successfully!",
        "notif_permission_denied": "❌ Notification permission was denied. Go to your browser/phone settings and re-enable notifications for this site.",
        "notif_not_supported": "⚠️ This browser does not support push notifications.",
        "notif_ios_warning": "⚠️ iPhone/iPad (Safari) does not support push notifications in the regular browser. Add SafePill to your Home Screen, and always watch for the red/yellow warning banners inside the app — this is the most reliable alert channel on iPhone.",
        "notif_ios_add_home_title": "📱 iPhone/iPad: add SafePill to your Home Screen for the most reliable alerts",
        "notif_ios_add_home_step1": "1️⃣ Tap the Share icon (square with an arrow) in Safari's bottom bar",
        "notif_ios_add_home_step2": "2️⃣ Choose \"Add to Home Screen\"",
        "notif_ios_add_home_step3": "3️⃣ Tap \"Add\", then always open SafePill from its Home Screen icon (not through Safari)",
        "notif_ios_add_home_note": "Note: even after adding to Home Screen, SafePill can only remind you while the app is open. Open the app around dosing times and watch for red/yellow banners inside the app.",
        "acc_personal_info": "Personal information",
        "acc_full_name": "Full name",
        "acc_blood_type": "🩸 Blood type",
        "acc_language": "🌐 Display language",
        "acc_save_btn": "Save information",
        "acc_error_empty_name": "❌ Full name cannot be empty.",
        "acc_missing_col_warn": "⚠️ The database is missing the 'blood_type'/'language' column(s). "
                                 "Please run the SQL migration to add it and save the full information.",
        "acc_update_success": "✅ Personal information updated.",
        "acc_update_error": "Update error:",
        "acc_change_pin": "Change PIN",
        "acc_current_pin": "Current PIN",
        "acc_new_pin": "New PIN",
        "acc_confirm_pin": "Confirm new PIN",
        "acc_change_pin_btn": "Change PIN",
        "acc_pin_error_empty": "❌ Please fill in all 3 fields.",
        "acc_pin_error_wrong": "❌ Current PIN is incorrect.",
        "acc_pin_error_format": "❌ New PIN must be exactly 4 digits.",
        "acc_pin_error_mismatch": "❌ PIN confirmation does not match.",
        "acc_pin_success": "✅ PIN changed successfully.",
        "acc_faceid_title": "FaceID",
        "acc_faceid_registered": "✅ FaceID is registered for this account.",
        "acc_faceid_not_registered": "ℹ️ FaceID is not registered for this account.",
        "acc_faceid_expander": "📷 Re-capture / register new FaceID",
        "acc_faceid_capture": "Take a photo of your face",
        "acc_faceid_save_btn": "Save FaceID",
        "acc_faceid_bad_image": "❌ Could not process the image, please try again.",
        "acc_faceid_saved": "✅ New FaceID saved.",
        "acc_faceid_save_error": "❌ Could not save FaceID (check whether the face_data/face_hash "
                                  "migration has been run):",
        "acc_faceid_remove_btn": "🗑️ Remove FaceID",
        "acc_faceid_removed": "✅ FaceID removed from this account.",
        "acc_faceid_remove_error": "Error removing FaceID:",

        "sched_title": "Adjust reminder times & dosage for each medication",
        "sched_empty": "No medications in your cabinet to schedule yet. Scan a prescription or add one manually.",
        "sched_med_fallback": "Medication #{n}",
        "sched_dose": "Dosage",
        "sched_time": "Exact reminder time",
        "sched_color": "Pill color",
        "sched_shape": "Shape",
        "sched_qty": "Quantity remaining",
        "sched_clinic": "Clinic / hospital",
        "sched_doctor": "Treating physician",
        "sched_pharmacy": "Pharmacy",
        "sched_save_btn": "Save changes",
        "sched_save_success": "✅ Reminder updated for {med}.",
        "sched_footer_caption": "💡 Reminder times and clinic/physician/pharmacy details are saved "
                                 "persistently to Supabase (the 'diagnostic' column), so they won't be "
                                 "lost on reload or re-login.",

        "notif_title": "Customize reminder notifications & sound",
        "notif_caption": "Sound plays alongside a browser notification on your phone/computer when it's "
                          "time to take a medication or a custom reminder. Notification permission is "
                          "required, and the SafePill tab must stay open (or run in the background) to "
                          "receive reminders.",
        "notif_sound_type": "Reminder sound type",
        "notif_sound_beep": "🔔 Beep (default)",
        "notif_sound_chime": "🎐 Chime (soft)",
        "notif_sound_bell": "🔔 Bell (loud)",
        "notif_volume": "Volume",
        "notif_saved": "✅ Reminder sound settings saved.",
        "notif_test_title": "**Test the sound:**",
        "notif_test_btn": "▶ Play test",
        "notif_tip_caption": "💡 Tip: on mobile, add SafePill to your home screen and allow browser "
                              "notifications for more reliable reminders.",
        "notif_tts_title": "🔊 Read aloud (Text-to-Speech)",
        "notif_tts_toggle": "Show the 🔊 read-aloud button for medication name/dosage in the Today tab",
        "notif_tts_caption": "👴 For elderly users who aren't comfortable with small text: tap the 🔊 "
                              "button next to each medication to hear its name, dosage, and time read "
                              "aloud by the browser's voice.",

        "family_title": "👪 Family members who remind me",
        "family_caption": "Invite a family member (who already has a SafePill account) so they can send "
                           "you reminders directly — for example, \"Remember to take your blood pressure "
                           "medicine!\". They need to sign in with their own phone number and accept the "
                           "invite before they can send reminders.",
        "family_invite_phone": "Family member's phone",
        "family_invite_name": "Nickname (optional)",
        "family_invite_name_placeholder": "E.g. Son",
        "family_invite_btn": "📨 Send invite",
        "family_invite_error_phone": "❌ Invalid phone number.",
        "family_invite_error_self": "❌ You can't invite yourself.",
        "family_invite_sent": "✅ Invite sent to {phone}.",
        "family_list_title": "**Family members:**",
        "family_status_pending": "⏳ Pending",
        "family_status_accepted": "✅ Accepted",
        "family_status_declined": "❌ Declined",
        "family_none": "No family members invited yet.",
        "family_delete_error": "❌ Could not remove the link:",
        "family_pending_title": "📥 Invites waiting for my approval",
        "family_owner_label": "Cabinet owner:",
        "family_accept_btn": "✅ Accept",
        "family_accept_success": "✅ You are now following this person as a family member.",
        "family_accept_error": "❌ Could not update the invite status. Common cause: the "
                                "'safepill_family_links' table is missing an RLS UPDATE policy for the "
                                "anon role. Details:",
        "family_decline_btn": "❌ Decline",
        "family_decline_error": "❌ Could not update the invite status:",
        "family_no_pending": "No pending invites.",
        "family_send_title": "📤 Send a reminder to someone I follow",
        "family_send_none": "No one has accepted you as their family member yet. Once someone invites you "
                             "and you accept above, they'll appear here so you can send them reminders.",
        "family_send_mode": "When to send",
        "family_send_now": "Send now",
        "family_send_scheduled": "Schedule a time",
        "family_send_pick_time": "Choose the hour and minute to send the reminder:",
        "family_send_hour": "Hour",
        "family_send_minute": "Minute",
        "family_send_target": "Send reminder to",
        "family_send_msg": "Reminder message",
        "family_send_msg_placeholder": "E.g. Don't forget your evening blood pressure medicine!",
        "family_send_btn": "📨 Send reminder",
        "family_send_warn_empty": "⚠️ Please enter a reminder message.",
        "family_send_success": "✅ Reminder sent! The recipient will see a notification with sound when "
                                "they open/have SafePill open (at the scheduled time, if set).",
        "family_send_error": "Error:",
        "family_footer_caption": "ℹ️ Note: reminders from family only appear and play sound when the "
                                  "recipient has SafePill open or reloads the page (no true background "
                                  "push notifications yet when the browser is closed).",
    },
}


def tr(key: str, **kwargs) -> str:
    """
    Trả về chuỗi đã dịch theo ngôn ngữ hiện tại trong session (mặc định 'vi' nếu chưa đăng nhập
    hoặc chưa có lựa chọn). Nếu thiếu key ở ngôn ngữ hiện tại, tự rơi về bản tiếng Việt; nếu
    vẫn thiếu, trả về chính key đó để dễ phát hiện lỗi thiếu bản dịch khi mở rộng.
    Hỗ trợ định dạng chuỗi kiểu .format(**kwargs), ví dụ: tr("home_low_stock", drug="Aspirin", qty=3)
    """
    lang = st.session_state.get("language", "vi")
    text = TRANSLATIONS.get(lang, TRANSLATIONS["vi"]).get(key)
    if text is None:
        text = TRANSLATIONS["vi"].get(key, key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text


def current_lang_name() -> str:
    """Tên ngôn ngữ hiện tại bằng chính ngôn ngữ đó, dùng khi cần chỉ định cho Gemini."""
    lang = st.session_state.get("language", "vi")
    return "tiếng Việt" if lang == "vi" else "English"


def render_language_switcher() -> None:
    """
    MỚI — Bộ chọn ngôn ngữ hiển thị TRƯỚC khi đăng nhập/đăng ký (ở màn Onboarding và màn Xác thực),
    để người dùng đổi ngôn ngữ ngay từ đầu, không cần đợi đến lúc đăng ký xong. Đặt ở góc phải màn
    hình, đổi giá trị là toàn bộ giao diện (kể cả 2 màn hình chưa đăng nhập) chuyển ngôn ngữ ngay lập
    tức nhờ rerun. Lựa chọn này chỉ áp dụng cho phiên hiện tại; sau khi đăng nhập, ngôn ngữ đã lưu
    trong hồ sơ (nếu có) sẽ ghi đè lại theo load_profile_into_session().
    """
    lc1, lc2 = st.columns([3, 1])
    with lc2:
        current = st.session_state.get("language", "vi")
        choice = st.selectbox(
            "🌐", options=list(LANGUAGE_OPTIONS.keys()),
            format_func=lambda k: LANGUAGE_OPTIONS[k],
            index=list(LANGUAGE_OPTIONS.keys()).index(current),
            key="pre_auth_language_switcher",
            label_visibility="collapsed",
        )
        if choice != current:
            st.session_state.language = choice
            st.rerun()

# =====================================================================================
# 2. KẾT NỐI DỊCH VỤ (Supabase + Gemini) - có kiểm tra lỗi rõ ràng
# =====================================================================================
def load_secrets():
    """
    Đọc cấu hình theo THỨ TỰ ƯU TIÊN sau, để Ban giám khảo chỉ cần điền trực tiếp vào
    file appsettings/appsettings.json (đổi tên từ appsettings.example.json) mà KHÔNG
    cần tạo thêm bất kỳ file .streamlit/secrets.toml nào:
      1) File appsettings/appsettings.json nằm cùng cấp với file .py này
      2) st.secrets — dùng khi triển khai trên Streamlit Community Cloud
    """
    config = {}
    json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "appsettings", "appsettings.json")
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception as e:
            st.error(f"❌ Không đọc được file appsettings/appsettings.json (sai định dạng JSON?): {e}")
            st.stop()

    def get_value(key):
        val = config.get(key)
        # Bỏ qua nếu vẫn còn là placeholder dạng "Điền ... vào đây" chưa được điền thật
        if val and "Điền" not in str(val) and str(val).strip():
            return val
        if key in st.secrets:
            return st.secrets[key]
        return None

    keys = ("SUPABASE_URL", "SUPABASE_KEY", "GEMINI_KEY")
    values = {k: get_value(k) for k in keys}
    missing = [k for k, v in values.items() if not v]
    if missing:
        st.error(
            f"❌ Thiếu cấu hình: {', '.join(missing)}. "
            f"Hãy mở file appsettings/appsettings.json (đổi tên từ appsettings.example.json, "
            f"đặt cùng thư mục với safepill.py) và điền đầy đủ URL/Key vào đó, rồi chạy lại ứng dụng."
        )
        st.stop()
    return values["SUPABASE_URL"], values["SUPABASE_KEY"], values["GEMINI_KEY"]


@st.cache_resource(show_spinner=False)
def init_connections():
    url, key, gemini_key = load_secrets()
    sb_client = create_client(url, key)
    ai_client = genai.Client(api_key=gemini_key)
    return sb_client, ai_client


try:
    supabase, ai_gemini = init_connections()
    SERVICES_OK = True
except Exception as e:
    SERVICES_OK = False
    st.error(f"❌ Không thể khởi tạo kết nối dịch vụ: {e}")
    st.stop()

TABLE = "thuy_tien"
# Bảng 'thuy_tien': id, phone, full_name, pin, health_tree_score, face_data, face_hash, blood_type,
# language, diagnostic
# Cột 'diagnostic' dùng để lưu tủ thuốc (kèm nơi khám/bác sĩ/nơi cấp thuốc) dưới dạng chuỗi JSON,
# nhờ đó dữ liệu không còn bị mất khi tải lại trang hoặc đăng xuất.
# Cột 'language' (MỚI) lưu ngôn ngữ hiển thị ưa thích ('vi' hoặc 'en'), cần chạy migration:
#   alter table thuy_tien add column if not exists language text default 'vi';
#
# ---- QUAN TRỌNG: đảm bảo 1 số điện thoại chỉ đăng ký được 1 tài khoản ----
# Ứng dụng đã kiểm tra trùng số điện thoại ở tầng code (xem phone_already_registered() và
# submit_reg bên dưới), nhưng để chống trường hợp 2 người bấm "Đăng ký" gần như đồng thời
# (race condition), NÊN thêm ràng buộc UNIQUE ngay trên cột 'phone' tại Supabase:
#   -- Bước 1: kiểm tra xem đã có số điện thoại trùng nhau trong bảng chưa
#   select phone, count(*) from thuy_tien group by phone having count(*) > 1;
#   -- Bước 2 (nếu bước 1 không trả về dòng nào): thêm ràng buộc duy nhất
#   alter table thuy_tien add constraint thuy_tien_phone_unique unique (phone);
# Nếu bước 1 phát hiện dữ liệu trùng sẵn có, cần xử lý (xoá/gộp) các bản ghi trùng trước khi
# chạy bước 2, nếu không lệnh ALTER TABLE sẽ báo lỗi.

# ---- Mới: bảng phục vụ tính năng "Nhắc nhở từ người thân" ----
# Cần tạo 2 bảng này bằng SQL migration trên Supabase trước khi dùng (nếu chưa có sẵn):
#
# create table safepill_family_links (
#     id bigserial primary key,
#     owner_phone text not null,        -- người được theo dõi (chủ tủ thuốc)
#     member_phone text not null,       -- người thân được phép gửi nhắc nhở
#     member_name text,
#     status text default 'pending',    -- 'pending' | 'accepted' | 'declined'
#     created_at timestamptz default now()
# );
#
# create table safepill_family_reminders (
#     id bigserial primary key,
#     owner_phone text not null,        -- người sẽ nhận nhắc nhở
#     sender_phone text,
#     sender_name text,
#     message text not null,
#     target_time text,                 -- 'HH:MM' hoặc NULL nếu gửi ngay lập tức
#     delivered boolean default false,
#     created_at timestamptz default now()
# );
FAMILY_LINKS_TABLE = "safepill_family_links"
FAMILY_REMINDERS_TABLE = "safepill_family_reminders"

# ---- Mới: bảng lưu lịch sử tuân thủ điều trị theo ngày (phục vụ biểu đồ & xuất báo cáo) ----
# create table safepill_adherence_history (
#     id bigserial primary key,
#     owner_phone text not null,
#     log_date date not null,
#     total_tasks int default 0,
#     done_tasks int default 0,
#     rate numeric default 0,
#     created_at timestamptz default now(),
#     unique (owner_phone, log_date)
# );
ADHERENCE_HISTORY_TABLE = "safepill_adherence_history"


# =====================================================================================
# 3. HÀM TIỆN ÍCH BẢO MẬT & XỬ LÝ DỮ LIỆU
# =====================================================================================
def hash_pin(pin: str) -> str:
    """Băm mã PIN bằng SHA-256 trước khi lưu trữ, không bao giờ lưu PIN dạng thô."""
    return hashlib.sha256(pin.strip().encode("utf-8")).hexdigest()
    
def verify_pin(entered_pin: str, stored_value: str) -> bool:
    """
    Hỗ trợ tương thích ngược: nếu bản ghi cũ còn lưu PIN dạng thô (4 ký tự),
    vẫn so khớp được; bản ghi mới (đã băm SHA-256 dài 64 ký tự) so khớp theo hash.
    """
    if not stored_value:
        return False
    stored_value = str(stored_value).strip()
    if len(stored_value) == 64:
        return hash_pin(entered_pin) == stored_value
    return str(entered_pin).strip() == stored_value


def validate_phone(phone: str) -> bool:
    return bool(re.match(r"^0\d{9}$", phone.strip()))


def phone_already_registered(phone: str) -> bool:
    """
    MỚI — Kiểm tra ở tầng ứng dụng xem số điện thoại đã có tài khoản hay chưa, TRƯỚC khi insert.
    Đây là lớp bảo vệ chính (không phụ thuộc vào việc bảng có ràng buộc UNIQUE hay không); nên
    kết hợp thêm ràng buộc UNIQUE(phone) ở Supabase (xem ghi chú tại phần khai báo TABLE) để chống
    trường hợp 2 yêu cầu đăng ký gửi lên gần như đồng thời (race condition).
    """
    try:
        res = supabase.table(TABLE).select("phone").eq("phone", phone.strip()).limit(1).execute()
        return bool(res.data)
    except Exception:
        # Nếu không kiểm tra được (lỗi kết nối...), vẫn để luồng insert phía sau tự bắt lỗi
        # trùng khoá (nếu bảng có UNIQUE constraint) thay vì chặn cứng người dùng.
        return False


# ---- Mới: danh sách nhóm máu để lưu vào hồ sơ, phục vụ cấp cứu khẩn cấp ----
BLOOD_TYPE_OPTIONS = ["Chưa rõ", "A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]


def average_hash(image_bytes: bytes, hash_size: int = 8) -> str:
    """
    Perceptual hash (aHash) đơn giản dùng để đối chiếu ảnh khuôn mặt ở mức demo.
    Đây KHÔNG phải nhận diện khuôn mặt sinh trắc học thật sự (không dùng embedding
    khuôn mặt chuyên dụng như FaceNet/Dlib) — phù hợp cho mục đích minh họa/khoa học
    kỹ thuật, và cần nâng cấp lên thư viện nhận diện khuôn mặt chuyên dụng khi triển
    khai thực tế.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("L").resize((hash_size, hash_size))
        pixels = list(img.getdata())
        avg = sum(pixels) / len(pixels)
        return "".join("1" if p > avg else "0" for p in pixels)
    except Exception:
        return ""


def hamming_distance(hash1: str, hash2: str) -> int:
    if not hash1 or not hash2 or len(hash1) != len(hash2):
        return 999
    return sum(c1 != c2 for c1, c2 in zip(hash1, hash2))


def extract_json_array(raw_text: str):
    """Trích xuất mảng JSON từ phản hồi AI dù có lẫn văn bản/markdown thừa."""
    cleaned = raw_text.strip()
    cleaned = re.sub(r"^```json", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = cleaned.replace("```", "").strip()
    match = re.search(r"\[.*\]", cleaned, re.DOTALL)
    if match:
        cleaned = match.group(0)
    return json.loads(cleaned)


def resolve_reminder_time(thoi_diem: str) -> str:
    """Chuyển 'Sáng/Trưa/Tối' hoặc giờ cụ thể (HH:MM) thành giờ HH:MM để đặt nhắc nhở."""
    if not thoi_diem:
        return "08:00"
    text = str(thoi_diem).strip()
    m = re.search(r"(\d{1,2}):(\d{2})", text)
    if m:
        h, mi = int(m.group(1)), int(m.group(2))
        if 0 <= h <= 23 and 0 <= mi <= 59:
            return f"{h:02d}:{mi:02d}"
    text_lower = text.lower()
    if "sáng" in text_lower or "morning" in text_lower:
        return "07:00"
    if "trưa" in text_lower or "noon" in text_lower:
        return "12:00"
    if "chiều" in text_lower or "afternoon" in text_lower:
        return "17:00"
    if "tối" in text_lower or "đêm" in text_lower or "evening" in text_lower or "night" in text_lower:
        return "19:00"
    return "08:00"


# Cơ sở dữ liệu tương tác thuốc lâm sàng (khai báo 1 chiều, hệ thống tự đối chiếu 2 chiều)
# ---- MỚI: mỗi cặp tương tác có thêm trường "nguon" ghi rõ tài liệu tham khảo uy tín đã
# đối chiếu (Dược thư Quốc gia Việt Nam, Drugs.com Interaction Checker...) để tăng độ tin cậy
# và minh bạch nguồn gốc thông tin. Khuyến nghị: trước khi triển khai thực tế, nhóm thực hiện
# nên phối hợp dược sĩ rà soát lại toàn bộ dữ liệu, đối chiếu trực tiếp với ấn bản mới nhất của
# Dược thư Quốc gia Việt Nam và cơ sở dữ liệu Drugs.com/Lexicomp trước khi dùng cho mục đích lâm sàng.
#
# LƯU Ý VỀ ĐA NGÔN NGỮ: mỗi cặp tương tác nay có thêm bản dịch tiếng Anh y khoa
# (các trường "*_en") do đội ngũ tự soạn dựa trên đúng nội dung tiếng Việt gốc, không dùng dịch
# máy tự động. Khi giao diện ở chế độ tiếng Anh, hàm loc_field() bên dưới sẽ ưu tiên lấy bản
# "*_en"; nếu thiếu sẽ tự rơi về bản tiếng Việt để không bao giờ hiển thị trống. Khuyến nghị:
# trước khi dùng cho mục đích lâm sàng thực tế, nên nhờ dược sĩ song ngữ rà soát lại các bản
# dịch này.
DEFAULT_SOURCE_NOTE = "Dược thư Quốc gia Việt Nam; Drugs.com Interaction Checker"
DEFAULT_SOURCE_NOTE_EN = "Vietnamese National Pharmacopoeia (Dược thư Quốc gia Việt Nam); Drugs.com Interaction Checker"


def loc_field(entry: dict, field: str) -> str:
    """
    Trả về giá trị đã bản địa hóa của một trường dữ liệu y khoa (severity/effect/item/nguon).
    Ưu tiên bản "{field}_en" khi ngôn ngữ hiện tại là 'en' và bản dịch đã tồn tại; nếu không,
    luôn rơi về bản tiếng Việt gốc để tránh hiển thị rỗng.
    """
    lang = st.session_state.get("language", "vi")
    if lang == "en":
        en_val = entry.get(f"{field}_en")
        if en_val:
            return en_val
    return entry.get(field, "")


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

# ---- MỚI: độ nguy hiểm khi BỎ LIỀU (khác với độ nguy hiểm khi TƯƠNG TÁC 2 thuốc) ----
# Dùng để quyết định có escalate cho người thân khi người dùng bấm "❌ Bỏ lỡ" liên tiếp hay không.
MISSED_DOSE_SEVERITY = {
    "Warfarin": "Nghiêm trọng", "Digoxin": "Nghiêm trọng", "Metformin": "Nghiêm trọng",
    "Aspirin": "Cao", "Simvastatin": "Cao", "Ibuprofen": "Cao",
    "Losartan": "Trung bình", "Clopidogrel": "Trung bình", "Paracetamol": "Trung bình",
}
DEFAULT_MISSED_DOSE_SEVERITY = "Trung bình"  # mặc định an toàn: vẫn escalate nếu bỏ lỡ nhiều lần


def get_missed_dose_severity(drug_name: str) -> str:
    return MISSED_DOSE_SEVERITY.get(drug_name.strip().capitalize(), DEFAULT_MISSED_DOSE_SEVERITY)
def build_symmetric_lookup(db: dict) -> dict:
    """Đảm bảo tra cứu được cả 2 chiều A→B và B→A dù dữ liệu chỉ khai báo 1 chiều."""
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


def check_interaction(drug_a: str, drug_b: str):
    a, b = drug_a.strip().capitalize(), drug_b.strip().capitalize()
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


# =====================================================================================
# 3A2. MỚI: TƯƠNG TÁC THUỐC – THỰC PHẨM / THẢO DƯỢC KIỂU VIỆT NAM
# =====================================================================================
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
    """Đối chiếu từng thuốc trong tủ thuốc với danh sách thực phẩm/thảo dược VN cần tránh phối hợp."""
    results = []
    for m in med_data:
        name = m.get("Tên thuốc", "").strip().capitalize()
        if name in VN_FOOD_HERB_DATABASE:
            for warn in VN_FOOD_HERB_DATABASE[name]:
                results.append({"thuoc": name, **warn})
    return results


def _strip_accents(text: str) -> str:
    """Bỏ dấu tiếng Việt để so khớp linh hoạt (VD: 'rượu' ~ 'ruou')."""
    normalized = unicodedata.normalize("NFD", text)
    without_marks = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    return without_marks.replace("đ", "d").replace("Đ", "D")


def _fuzzy_food_item_match(user_input: str, item_field: str) -> bool:
    """
    So khớp linh hoạt giữa nội dung người dùng gõ (VD: "rượu", "bưởi") và trường "item"
    trong VN_FOOD_HERB_DATABASE (VD: "Rượu bia", "Nước ép bưởi / bưởi") — không phân biệt
    hoa/thường, không phân biệt dấu, và tách theo từng cụm ngăn cách bởi "/" hoặc ",".
    """
    if not user_input or not user_input.strip():
        return False
    ui = _strip_accents(user_input).strip().lower()
    for part in re.split(r"[/,]", item_field):
        p = _strip_accents(part).strip().lower()
        # Bỏ phần chú thích trong ngoặc để so khớp gọn hơn, VD: "Thuốc nam (đương quy...)"
        p_main = re.sub(r"\(.*?\)", "", p).strip()
        if not p_main:
            continue
        if ui in p_main or p_main in ui:
            return True
    return False


def check_food_herb_pair(input_a: str, input_b: str) -> list:
    """
    MỚI — Dùng cho công cụ tra cứu thủ công (tab "Tra cứu tương tác"): người dùng có thể gõ
    một thuốc và MỘT THỰC PHẨM/THẢO DƯỢC (VD: Aspirin + rượu) chứ không chỉ hai tên thuốc.
    check_interaction() chỉ tra trong INTERACTION_DATABASE (thuốc–thuốc) nên trước đây bỏ sót
    hoàn toàn các cặp thuốc–thực phẩm dù VN_FOOD_HERB_DATABASE đã có sẵn dữ liệu. Hàm này đối
    chiếu CẢ HAI CHIỀU nhập liệu với VN_FOOD_HERB_DATABASE để không bỏ sót cảnh báo.
    """
    results = []
    a_clean, b_clean = input_a.strip(), input_b.strip()
    a_key, b_key = a_clean.capitalize(), b_clean.capitalize()

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
# 3B. HÀM TIỆN ÍCH: NHẮC NHỞ TỪ NGƯỜI THÂN (Supabase)
# =====================================================================================
FAMILY_TABLE_MISSING_MSG = (
    "⚠️ Chưa thể dùng tính năng người thân vì cơ sở dữ liệu chưa có bảng "
    "'safepill_family_links' / 'safepill_family_reminders'. Hãy chạy migration SQL "
    "(xem ghi chú phía trên phần khai báo TABLE trong code) rồi tải lại trang."
)


def _is_missing_table_error(err) -> bool:
    """
    SỬA LỖI — nhận diện lỗi thiếu bảng qua nhiều dấu hiệu phổ biến của PostgREST/PostgreSQL.
    """
    text = str(err).lower()
    signals = (
        "relation", "does not exist", "could not find the table",
        "schema cache", "pgrst205", "42p01",
    )
    return any(sig in text for sig in signals)


def create_family_invite(owner_phone: str, member_phone: str, member_name: str = "") -> tuple:
    """Chủ tủ thuốc (owner) mời một số điện thoại người thân (member) theo dõi/nhắc nhở mình."""
    try:
        supabase.table(FAMILY_LINKS_TABLE).insert({
            "owner_phone": owner_phone,
            "member_phone": member_phone.strip(),
            "member_name": member_name.strip(),
            "status": "pending",
        }).execute()
        return True, None
    except Exception as e:
        return False, str(e)


def fetch_family_members(owner_phone: str) -> list:
    """Danh sách người thân đã liên kết (mọi trạng thái) với owner_phone."""
    try:
        res = supabase.table(FAMILY_LINKS_TABLE).select("*").eq("owner_phone", owner_phone).execute()
        return res.data or []
    except Exception:
        return []


def fetch_pending_invites_for_member(member_phone: str) -> list:
    """Lời mời đang chờ chính người dùng (với vai trò người thân) phê duyệt."""
    try:
        res = (supabase.table(FAMILY_LINKS_TABLE).select("*")
               .eq("member_phone", member_phone).eq("status", "pending").execute())
        return res.data or []
    except Exception:
        return []


def fetch_owners_i_help(member_phone: str) -> list:
    """Danh sách chủ tủ thuốc mà người dùng hiện tại (với vai trò người thân) đã được chấp nhận theo dõi."""
    try:
        res = (supabase.table(FAMILY_LINKS_TABLE).select("*")
               .eq("member_phone", member_phone).eq("status", "accepted").execute())
        return res.data or []
    except Exception:
        return []


def update_family_link_status(link_id, new_status: str) -> tuple:
    try:
        supabase.table(FAMILY_LINKS_TABLE).update({"status": new_status}).eq("id", link_id).execute()
        return True, None
    except Exception as e:
        return False, str(e)


def delete_family_link(link_id) -> tuple:
    try:
        supabase.table(FAMILY_LINKS_TABLE).delete().eq("id", link_id).execute()
        return True, None
    except Exception as e:
        return False, str(e)


def send_family_reminder(owner_phone: str, sender_phone: str, sender_name: str,
                          message: str, target_time: str = None) -> tuple:
    """Người thân gửi một nhắc nhở đến owner_phone (gửi ngay nếu target_time=None)."""
    try:
        supabase.table(FAMILY_REMINDERS_TABLE).insert({
            "owner_phone": owner_phone,
            "sender_phone": sender_phone,
            "sender_name": sender_name,
            "message": message.strip(),
            "target_time": target_time,
            "delivered": False,
        }).execute()
        return True, None
    except Exception as e:
        return False, str(e)


def fetch_due_family_reminders(owner_phone: str) -> list:
    """
    Lấy các nhắc nhở của người thân dành cho owner_phone mà CHƯA hiển thị, và đã đến hạn.
    """
    try:
        res = (supabase.table(FAMILY_REMINDERS_TABLE).select("*")
               .eq("owner_phone", owner_phone).eq("delivered", False).execute())
        rows = res.data or []
    except Exception:
        return []
    now_hhmm = datetime.now().strftime("%H:%M")
    due = []
    for row in rows:
        t = row.get("target_time")
        if not t or t <= now_hhmm:
            due.append(row)
    return due


def mark_family_reminder_delivered(reminder_id) -> None:
    try:
        supabase.table(FAMILY_REMINDERS_TABLE).update({"delivered": True}).eq("id", reminder_id).execute()
    except Exception:
        pass


def send_escalation_alert_to_family(owner_phone: str, owner_name: str, drug_name: str, miss_count: int) -> list:
    """
    MỚI — Cảnh báo leo thang tự động: khi người dùng bỏ lỡ liên tiếp một thuốc mức độ
    nghiêm trọng, tự động gửi cảnh báo tới TẤT CẢ người thân đã 'accepted' của owner_phone.
    """
    members = fetch_family_members(owner_phone)
    accepted = [m for m in members if m.get("status") == "accepted"]
    sent_to = []
    alert_msg = (f"🚨 CẢNH BÁO: {owner_name or owner_phone} đã bỏ lỡ {miss_count} lần liên tiếp "
                 f"thuốc '{drug_name}' (mức độ nghiêm trọng cao). Vui lòng gọi điện hỏi thăm ngay!")
    for member in accepted:
        member_phone = member.get("member_phone")
        if not member_phone:
            continue
        ok, _ = send_family_reminder(
            owner_phone=member_phone,
            sender_phone=owner_phone,
            sender_name=f"{owner_name or owner_phone} (Cảnh báo tự động SafePill)",
            message=alert_msg,
            target_time=None,
        )
        if ok:
            sent_to.append(member_phone)
    return sent_to


def record_missed_dose(drug_name: str, severity: str) -> int:
    """Tăng bộ đếm bỏ lỡ liên tiếp cho một thuốc; trả về số lần bỏ lỡ liên tiếp hiện tại."""
    st.session_state.missed_streak[drug_name] = st.session_state.missed_streak.get(drug_name, 0) + 1
    return st.session_state.missed_streak[drug_name]


def reset_missed_dose(drug_name: str) -> None:
    st.session_state.missed_streak[drug_name] = 0


AUTO_ESCALATION_MINUTES = 30


def build_adherence_task_key(drug_name: str, hhmm: str, med_obj) -> str:
    """
    Sinh key nhắc nhở DUY NHẤT và NHẤT QUÁN cho một task (thuốc + giờ hẹn).
    """
    return f"task_{drug_name}_{hhmm}_{id(med_obj)}"


def check_and_auto_escalate_overdue_doses(med_data_valid: list) -> list:
    """
    Rà soát các thuốc trong lịch hôm nay: nếu đã quá AUTO_ESCALATION_MINUTES phút kể từ giờ hẹn
    mà vẫn CHƯA được đánh dấu 'Đã uống', tự động gửi cảnh báo tới toàn bộ người thân đã 'accepted'
    (nếu có) VÀ luôn trả về mục đó để hiển thị cảnh báo cho chính người dùng trên UI — không phụ
    thuộc vào việc có người thân hay gửi thành công hay không.
    """
    now = datetime.now()
    newly_escalated = []
    for med in med_data_valid:
        drug_name = med.get("Tên thuốc", "")
        hhmm = resolve_reminder_time(med.get("Thời điểm", ""))
        key_name = build_adherence_task_key(drug_name, hhmm, med)
        if st.session_state.adherence_logs.get(key_name, False):
            continue
        if key_name in st.session_state.auto_escalated_keys:
            continue
        try:
            h, mi = map(int, hhmm.split(":"))
            scheduled_dt = now.replace(hour=h, minute=mi, second=0, microsecond=0)
        except Exception:
            continue
        minutes_overdue = (now - scheduled_dt).total_seconds() / 60
        if minutes_overdue >= AUTO_ESCALATION_MINUTES:
            sent_to = send_escalation_alert_to_family(
                st.session_state.user_phone,
                st.session_state.current_profile.get("full_name", ""),
                f"{drug_name} (giờ hẹn {hhmm}, đã quá {AUTO_ESCALATION_MINUTES} phút chưa xác nhận uống)",
                1,
            )
            st.session_state.auto_escalated_keys.add(key_name)
            # LUÔN thêm vào danh sách hiển thị cho người dùng, kể cả khi chưa có người thân
            newly_escalated.append({"drug": drug_name, "time": hhmm, "sent_to": len(sent_to)})
    return newly_escalated
   


LOW_STOCK_THRESHOLD = 5


def decrement_med_quantity(med_idx: int, task_key: str) -> None:
    """Trừ 1 đơn vị khỏi 'Số lượng còn lại' của thuốc khi được đánh dấu 'Đã uống'."""
    already = st.session_state.qty_decremented.get(task_key, False)
    if already:
        return
    med = st.session_state.med_data[med_idx]
    qty = med.get("Số lượng còn lại")
    if qty is not None:
        try:
            qty_val = int(qty)
            med["Số lượng còn lại"] = max(0, qty_val - 1)
        except (TypeError, ValueError):
            pass
    st.session_state.qty_decremented[task_key] = True


def restore_med_quantity(med_idx: int, task_key: str) -> None:
    """Hoàn tác trừ số lượng nếu người dùng bỏ tick 'Đã uống'."""
    if not st.session_state.qty_decremented.get(task_key, False):
        return
    med = st.session_state.med_data[med_idx]
    qty = med.get("Số lượng còn lại")
    if qty is not None:
        try:
            qty_val = int(qty)
            med["Số lượng còn lại"] = qty_val + 1
        except (TypeError, ValueError):
            pass
    st.session_state.qty_decremented[task_key] = False


def log_adherence_snapshot(owner_phone: str, total_tasks: int, done_tasks: int) -> tuple:
    """Ghi/cập nhật (upsert) tỷ lệ tuân thủ của HÔM NAY vào Supabase để dựng biểu đồ theo thời gian."""
    if total_tasks == 0:
        return True, None
    rate = round((done_tasks / total_tasks) * 100, 1)
    today_str = datetime.now().strftime("%Y-%m-%d")
    try:
        supabase.table(ADHERENCE_HISTORY_TABLE).upsert({
            "owner_phone": owner_phone,
            "log_date": today_str,
            "total_tasks": total_tasks,
            "done_tasks": done_tasks,
            "rate": rate,
        }, on_conflict="owner_phone,log_date").execute()
        return True, None
    except Exception as e:
        return False, str(e)


def fetch_adherence_history(owner_phone: str, days: int = 30) -> list:
    try:
        since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        res = (supabase.table(ADHERENCE_HISTORY_TABLE).select("*")
               .eq("owner_phone", owner_phone).gte("log_date", since)
               .order("log_date").execute())
        return res.data or []
    except Exception:
        return []


ADHERENCE_HISTORY_MISSING_MSG = (
    "⚠️ Chưa thể lưu/hiển thị lịch sử tuân thủ vì cơ sở dữ liệu chưa có bảng "
    "'safepill_adherence_history'. Hãy chạy migration SQL (xem ghi chú tại phần khai báo "
    "ADHERENCE_HISTORY_TABLE trong code) rồi tải lại trang."
)


def build_emergency_qr_text(profile: dict, med_data: list, conflicts: list, family_members: list) -> str:
    """Dựng nội dung văn bản gọn gàng để mã hoá vào QR khẩn cấp."""
    lines = [
        "=== SAFEPILL - THE KHAN CAP ===",
        f"Ho ten: {profile.get('full_name', 'N/A')}",
        f"SDT: {profile.get('phone', 'N/A')}",
        f"Nhom mau: {profile.get('blood_type') or 'Chua ro'}",
        "--- Danh sach thuoc dang dung ---",
    ]

    valid_meds = [m for m in med_data if m.get('Tên thuốc')]
    if valid_meds:
        for m in valid_meds[:4]:
            lines.append(f"- {m.get('Tên thuốc', '')} | Lieu: {m.get('Liều lượng', '')}")
    else:
        lines.append("(Chua co du lieu thuoc)")

    accepted_family = [m for m in family_members if m.get("status") == "accepted"] if family_members else []
    if accepted_family:
        lines.append("--- Lien he nguoi than ---")
        for fm in accepted_family[:2]:
            lines.append(f"- {fm.get('member_name') or 'Nguoi than'}: {fm.get('member_phone', '')}")

    return "\n".join(lines)


def generate_qr_image(text: str):
    """Trả về ảnh PIL của mã QR chứa `text`, hoặc None nếu thư viện qrcode chưa được cài."""
    if not QRCODE_AVAILABLE:
        return None

    clean_text = str(text) if text else "N/A"

    if len(clean_text) > 1000:
        clean_text = clean_text[:950] + "\n...(Da cat bớt do qua dai)"

    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=8,
        border=3,
    )

    try:
        qr.add_data(clean_text)
        qr.make(fit=True)
        return qr.make_image(fill_color="black", back_color="white").convert("RGB")
    except Exception:
        qr_safe = qrcode.QRCode(
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=8,
            border=3,
        )
        qr_safe.add_data(clean_text[:500])
        qr_safe.make(fit=True)
        return qr_safe.make_image(fill_color="black", back_color="white").convert("RGB")


WALLPAPER_SIZES = {
    "iPhone (1170 x 2532)": (1170, 2532),
    "Android phổ biến (1080 x 2340)": (1080, 2340),
    "Vuông / máy tính bảng (1200 x 1600)": (1200, 1600),
}


def _load_font(size: int, bold: bool = False):
    from PIL import ImageFont
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def generate_lockscreen_wallpaper(qr_img, profile: dict, conflicts: list, size_key: str = "iPhone (1170 x 2532)"):
    """
    Ghép mã QR khẩn cấp vào một ảnh nền dọc kèm dòng chữ cảnh báo lớn, để đặt làm hình nền
    màn hình khoá.
    """
    from PIL import Image as PILImage, ImageDraw

    width, height = WALLPAPER_SIZES.get(size_key, (1170, 2532))
    bg_color = (0, 40, 37)
    accent_color = (255, 90, 90)
    canvas = PILImage.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(canvas)

    top_margin = int(height * 0.16)
    bottom_margin = int(height * 0.10)

    title_font = _load_font(int(width * 0.062), bold=True)
    name_font = _load_font(int(width * 0.045), bold=True)
    info_font = _load_font(int(width * 0.036))
    small_font = _load_font(int(width * 0.030))

    lang = st.session_state.get("language", "vi")
    title_text = "❗ THÔNG TIN Y TẾ KHẨN CẤP" if lang == "vi" else "❗ EMERGENCY MEDICAL INFORMATION"

    y = top_margin
    tw = draw.textlength(title_text, font=title_font)
    draw.text(((width - tw) / 2, y), title_text, font=title_font, fill=accent_color)
    y += int(width * 0.062) + 24

    qr_size = int(width * 0.62)
    qr_resized = qr_img.resize((qr_size, qr_size))
    pad = 24
    quiet_box = PILImage.new("RGB", (qr_size + pad * 2, qr_size + pad * 2), (255, 255, 255))
    quiet_box.paste(qr_resized, (pad, pad))
    qx = (width - quiet_box.width) // 2
    canvas.paste(quiet_box, (qx, y))
    y += quiet_box.height + 36

    name_fallback = "Chưa cập nhật tên" if lang == "vi" else "Name not set"
    name_text = profile.get("full_name", "") or name_fallback
    nw = draw.textlength(name_text, font=name_font)
    draw.text(((width - nw) / 2, y), name_text, font=name_font, fill=(255, 255, 255))
    y += int(width * 0.045) + 14

    blood_type = profile.get("blood_type")
    if blood_type and blood_type != "Chưa rõ":
        blood_prefix = "🩸 Nhóm máu:" if lang == "vi" else "🩸 Blood type:"
        blood_text = f"{blood_prefix} {blood_type}"
        bw = draw.textlength(blood_text, font=name_font)
        draw.text(((width - bw) / 2, y), blood_text, font=name_font, fill=accent_color)
        y += int(width * 0.045) + 14

    phone_prefix = "SĐT:" if lang == "vi" else "Phone:"
    phone_text = f"{phone_prefix} {profile.get('phone', '')}"
    pw = draw.textlength(phone_text, font=info_font)
    draw.text(((width - pw) / 2, y), phone_text, font=info_font, fill=(220, 230, 228))
    y += int(width * 0.036) + 14

    if conflicts:
        warn_text = (f"⚠️ Có {len(conflicts)} cảnh báo tương tác thuốc — xem chi tiết khi quét mã"
                     if lang == "vi" else
                     f"⚠️ {len(conflicts)} drug interaction warning(s) — scan for details")
        ww = draw.textlength(warn_text, font=info_font)
        draw.text(((width - ww) / 2, y), warn_text, font=info_font, fill=accent_color)
        y += int(width * 0.036) + 14

    footer_text = ("Quét mã QR để xem đầy đủ danh sách thuốc & liên hệ người thân — SafePill"
                   if lang == "vi" else
                   "Scan the QR code for the full medication list & family contacts — SafePill")
    fw = draw.textlength(footer_text, font=small_font)
    draw.text(((width - fw) / 2, height - bottom_margin), footer_text, font=small_font, fill=(180, 195, 192))

    return canvas


SHAPE_ICON_MAP = {
    "tròn": "border-radius:50%;", "round": "border-radius:50%;",
    "oval": "border-radius:50%;transform:scaleX(1.6);",
    "vien nen": "border-radius:6px;", "viên nén": "border-radius:6px;", "tablet": "border-radius:6px;",
    "vuông": "border-radius:4px;", "square": "border-radius:4px;",
    "con nhộng": "border-radius:50px;transform:scaleX(0.6) scaleY(1.4);",
    "capsule": "border-radius:50px;transform:scaleX(0.6) scaleY(1.4);",
}


def render_pill_icon_html(color: str, shape: str, size: int = 26) -> str:
    """Trả về đoạn HTML nhỏ vẽ hình viên thuốc (màu + hình dạng) để người già dễ nhận diện qua hình ảnh."""
    color_clean = (color or "#cccccc").strip()
    shape_key = (shape or "").strip().lower()
    shape_style = "border-radius:50%;"
    for key, style in SHAPE_ICON_MAP.items():
        if key in shape_key:
            shape_style = style
            break
    safe_color = color_clean if re.match(r"^#?[0-9a-fA-F]{3,8}$", color_clean) or re.match(
        r"^[a-zA-Z]+$", color_clean) else "#cccccc"
    return (f'<span style="display:inline-block;width:{size}px;height:{size}px;'
            f'background:{safe_color};{shape_style}border:1px solid #999;'
            f'vertical-align:middle;margin-right:6px;"></span>')


def build_tts_button_html(text: str, button_label: str = "🔊", key_suffix: str = "") -> str:
    """Trả về HTML nút bấm phát âm thanh đọc to `text` bằng giọng của trình duyệt, theo ngôn ngữ hiện tại."""
    safe_text = json.dumps(text, ensure_ascii=False)
    btn_id = f"ttsBtn_{key_suffix}".replace(" ", "_")
    lang = st.session_state.get("language", "vi")
    speech_lang = "vi-VN" if lang == "vi" else "en-US"
    return f"""
    <button id="{btn_id}" style="padding:6px 12px;border-radius:8px;border:none;
    background:#006a62;color:white;cursor:pointer;font-size:13px;">{button_label}</button>
    <script>
    document.getElementById("{btn_id}").addEventListener("click", function() {{
        try {{
            const utter = new SpeechSynthesisUtterance({safe_text});
            utter.lang = "{speech_lang}";
            utter.rate = 0.95;
            window.speechSynthesis.cancel();
            window.speechSynthesis.speak(utter);
        }} catch (e) {{}}
    }});
    </script>
    """


# =====================================================================================
# 4. TRẠNG THÁI PHIÊN LÀM VIỆC
# =====================================================================================
DEFAULT_STATE = {
    "onboarded": False,
    "logged_in": False,
    "user_phone": None,
    "elderly_mode": False,
    "chat_history": [],
    "med_data": [],
    "current_profile": {},
    "adherence_logs": {},
    "reg_face_base64": None,
    "custom_reminders": [],
    "reminder_sound": "beep",
    "reminder_volume": 0.6,
    "missed_streak": {},
    "qty_decremented": {},
    "tts_enabled": True,
    "adherence_logged_today": False,
    "auto_escalated_keys": lambda: set(),
    "adherence_log_date": None,
    # ---- MỚI: ngôn ngữ hiển thị hiện tại của phiên làm việc ('vi' hoặc 'en') ----
    "language": "vi",
}
for key, default_val in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = default_val() if callable(default_val) else default_val


def reset_daily_adherence_state_if_needed() -> None:
    """
    Nếu sang ngày mới, tự động làm mới các bộ đếm tuân thủ để phản ánh đúng ngày hiện tại.
    """
    today_str = datetime.now().strftime("%Y-%m-%d")
    if st.session_state.adherence_log_date != today_str:
        st.session_state.adherence_logs = {}
        st.session_state.missed_streak = {}
        st.session_state.qty_decremented = {}
        st.session_state.auto_escalated_keys = set()
        st.session_state.adherence_logged_today = False
        st.session_state.adherence_log_date = today_str


def load_profile_into_session(user_row: dict):
    st.session_state.logged_in = True
    st.session_state.user_phone = user_row.get("phone")
    st.session_state.current_profile = user_row
    # ---- MỚI: áp dụng lại ngôn ngữ đã lưu của người dùng khi đăng nhập ----
    saved_lang = user_row.get("language")
    st.session_state.language = saved_lang if saved_lang in LANGUAGE_OPTIONS else "vi"
    diag = user_row.get("diagnostic")
    if diag and str(diag).startswith("["):
        try:
            st.session_state.med_data = json.loads(diag)
        except Exception:
            st.session_state.med_data = []


def save_med_data_to_supabase() -> None:
    """Ghi toàn bộ tủ thuốc hiện tại xuống cột 'diagnostic' của Supabase dưới dạng chuỗi JSON."""
    if not st.session_state.get("user_phone"):
        return
    try:
        supabase.table(TABLE).update({
            "diagnostic": json.dumps(st.session_state.med_data, ensure_ascii=False)
        }).eq("phone", st.session_state.user_phone).execute()
    except Exception as e:
        st.warning(f"⚠️ Không lưu được tủ thuốc lên máy chủ (dữ liệu chỉ tồn tại tạm trong phiên "
                   f"làm việc này): {e}")


def build_reminder_sound_script(sound_type: str, volume: float) -> str:
    """Trả về đoạn JS dùng chung để phát âm thanh nhắc nhở bằng Web Audio API."""
    return f"""
    function playReminderSound(type, volume) {{
        try {{
            const ctx = new (window.AudioContext || window.webkitAudioContext)();
            function tone(freq, start, dur) {{
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.frequency.value = freq;
                osc.type = 'sine';
                gain.gain.value = volume;
                osc.connect(gain);
                gain.connect(ctx.destination);
                osc.start(ctx.currentTime + start);
                osc.stop(ctx.currentTime + start + dur);
            }}
            if (type === 'chime') {{
                tone(523.25, 0, 0.2); tone(659.25, 0.2, 0.2); tone(783.99, 0.4, 0.3);
            }} else if (type === 'bell') {{
                tone(660, 0, 0.6); tone(880, 0.1, 0.5);
            }} else {{
                tone(880, 0, 0.15); tone(880, 0.25, 0.15);
            }}
        }} catch (e) {{}}
    }}
    """


# =====================================================================================
# MÀN HÌNH 1: ONBOARDING
# =====================================================================================
if not st.session_state.onboarded:
    render_language_switcher()
    st.markdown(f"<h1 style='text-align:center;color:#006a62;'>{tr('app_title')}</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align:center;color:#555;'>{tr('app_tagline')}</p>", unsafe_allow_html=True)
    onboarding_html = f"""
    <div style="display:flex;justify-content:center;font-family:sans-serif;">
      <div style="box-sizing:border-box;width:320px;background:#ffffff;border-radius:32px;
      border:6px solid #1e293b;overflow:hidden;box-shadow:0 20px 40px -12px rgba(0,0,0,.45);
      padding:0 0 20px 0;">
        <img src="https://images.unsplash.com/photo-1576091160550-2173dba999ef?w=400"
        style="display:block;width:100%;height:150px;object-fit:cover;" />
        <div style="box-sizing:border-box;width:100%;padding:16px 18px 0 18px;text-align:center;">
          <h2 style="margin:0 0 8px 0;font-size:1.2rem;font-weight:700;color:#1e293b;">
            {tr('onboarding_card_title')}
          </h2>
          <p style="margin:0;font-size:0.85rem;line-height:1.5;color:#64748b;
          word-wrap:break-word;overflow-wrap:break-word;white-space:normal;">
            {tr('onboarding_card_desc')}
          </p>
        </div>
      </div>
    </div>
    """
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        components.html(onboarding_html, height=330, scrolling=False)
        if st.button(tr("start_button"), type="primary", use_container_width=True):
            st.session_state.onboarded = True
            st.rerun()
    st.caption(tr("disclaimer"))
# =====================================================================================
# MÀN HÌNH 2: XÁC THỰC (ĐĂNG NHẬP / ĐĂNG KÝ 5 CHẠM)
# =====================================================================================
elif not st.session_state.logged_in:
    render_language_switcher()
    c1, c2, c3 = st.columns([1, 1.6, 1])
    with c2:
        st.markdown(f"<h2 style='text-align:center;color:#006a62;'>{tr('auth_header')}</h2>",
                    unsafe_allow_html=True)
        tab_login, tab_register = st.tabs([tr("tab_login"), tr("tab_register")])
        # ---------------- ĐĂNG NHẬP (Mã PIN hoặc FaceID) ----------------
        with tab_login:
            method = st.radio(tr("login_method_label"), [tr("login_pin"), tr("login_face")], horizontal=True)
            if method == tr("login_pin"):
                l_phone = st.text_input(tr("phone_label"), placeholder=tr("phone_placeholder"))
                l_pin = st.text_input(tr("pin_label"), type="password", max_chars=4, placeholder="****")
                if st.button(tr("login_button"), type="primary", use_container_width=True):
                    l_phone_clean = l_phone.replace(" ", "").strip()
                    l_pin_clean = l_pin.strip()
                    if not l_phone_clean or not l_pin_clean:
                        st.warning(tr("login_warning_empty"))
                    else:
                        with st.spinner(tr("login_authenticating")):
                            try:
                                res = supabase.table(TABLE).select("*").eq("phone", l_phone_clean).execute()
                                if res.data:
                                    user_row = res.data[0]
                                    if verify_pin(l_pin_clean, user_row.get("pin")):
                                        load_profile_into_session(user_row)
                                        st.success(tr("login_success"))
                                        st.rerun()
                                    else:
                                        st.error(tr("login_wrong_pin"))
                                else:
                                    st.error(tr("login_phone_not_found"))
                            except Exception as e:
                                st.error(f"{tr('login_db_error')} {e}")
            else:  # FaceID
                st.info(tr("face_login_hint"))
                face_img = st.camera_input(tr("face_login_capture"), key="face_login")
                if face_img:
                    with st.spinner(tr("face_login_matching")):
                        try:
                            login_hash = average_hash(face_img.getvalue())
                            if not login_hash:
                                st.error(tr("face_login_bad_image"))
                            else:
                                try:
                                    res = supabase.table(TABLE).select("phone, full_name, pin, face_hash").execute()
                                except Exception as col_err:
                                    st.error(tr("face_login_missing_col"))
                                    res = None
                                if res is not None:
                                    candidates = [row for row in (res.data or []) if row.get("face_hash")]
                                    best_match, best_distance = None, 999
                                    for row in candidates:
                                        dist = hamming_distance(login_hash, row["face_hash"])
                                        if dist < best_distance:
                                            best_distance, best_match = dist, row
                                    FACE_MATCH_THRESHOLD = 10
                                    if not candidates:
                                        st.warning(tr("face_login_no_accounts"))
                                    elif best_match and best_distance <= FACE_MATCH_THRESHOLD:
                                        full_res = supabase.table(TABLE).select("*").eq(
                                            "phone", best_match["phone"]
                                        ).execute()
                                        if full_res.data:
                                            load_profile_into_session(full_res.data[0])
                                            st.success(f"{tr('face_login_welcome')} "
                                                       f"{best_match.get('full_name', '')}.")
                                            st.rerun()
                                        else:
                                            st.error(tr("face_login_profile_fail"))
                                    else:
                                        st.error(tr("face_login_no_match"))
                        except Exception as e:
                            st.error(f"{tr('face_login_error')} {e}")
        # ---------------- ĐĂNG KÝ NHANH ----------------
        with tab_register:
            st.caption(tr("register_caption"))
            with st.form("quick_register_form", clear_on_submit=False):
                r_phone = st.text_input(f"📱 {tr('phone_label')}", placeholder=tr("phone_placeholder"))
                r_name = st.text_input(tr("full_name_label"), placeholder=tr("full_name_placeholder"))
                pin_col1, pin_col2 = st.columns([3, 1])
                with pin_col1:
                    r_pin = st.text_input(tr("pin_create_label"), type="password", max_chars=4, placeholder="****")
                with pin_col2:
                    show_pin = st.checkbox(tr("pin_show_checkbox"), help=tr("pin_show_help"))
                if show_pin and r_pin:
                    st.caption(f"{tr('pin_entered_caption')} `{r_pin}`")
                r_blood_type = st.selectbox(
                    tr("blood_type_label"), BLOOD_TYPE_OPTIONS, help=tr("blood_type_help"),
                )
                # ---- MỚI: chọn ngôn ngữ hiển thị ngay khi đăng ký — mặc định theo lựa chọn
                # người dùng đã chọn ở bộ chuyển ngôn ngữ phía trên (render_language_switcher),
                # để không bị "nhảy" ngược lại tiếng Việt nếu họ đã chọn English từ trước. ----
                r_language = st.selectbox(
                    tr("language_label"), options=list(LANGUAGE_OPTIONS.keys()),
                    format_func=lambda k: LANGUAGE_OPTIONS[k],
                    index=list(LANGUAGE_OPTIONS.keys()).index(st.session_state.get("language", "vi")),
                    key="reg_language",
                )
                enable_face = st.checkbox(tr("enable_face_checkbox"), value=False)
                reg_face_img = None
                if enable_face:
                    reg_face_img = st.camera_input(tr("face_capture_label"), key="register_face_cam")
                submit_reg = st.form_submit_button(tr("register_button"), use_container_width=True, type="primary")
                if submit_reg:
                    r_phone_clean, r_name_clean, r_pin_clean = r_phone.strip(), r_name.strip(), r_pin.strip()
                    if not r_phone_clean or not r_name_clean or not r_pin_clean:
                        st.error(tr("register_error_required"))
                    elif not validate_phone(r_phone_clean):
                        st.error(tr("register_error_phone"))
                    elif len(r_pin_clean) != 4 or not r_pin_clean.isdigit():
                        st.error(tr("register_error_pin"))
                    elif r_blood_type == "Chưa rõ":
                        st.error(tr("register_error_blood"))
                    elif enable_face and reg_face_img is None:
                        st.error(tr("register_error_face_missing"))
                    elif phone_already_registered(r_phone_clean):
                        st.error(tr("register_error_duplicate_phone", phone=r_phone_clean))
                    else:
                        with st.spinner(tr("register_initializing")):
                            try:
                                new_row = {
                                    "phone": r_phone_clean,
                                    "pin": hash_pin(r_pin_clean),
                                    "full_name": r_name_clean,
                                    "blood_type": r_blood_type,
                                    "language": r_language,
                                }
                                face_hash = None
                                if enable_face and reg_face_img is not None:
                                    face_bytes = reg_face_img.getvalue()
                                    face_hash = average_hash(face_bytes)
                                    if not face_hash:
                                        st.warning(tr("register_warning_face_fail"))
                                    else:
                                        new_row["face_data"] = base64.b64encode(face_bytes).decode("utf-8")
                                        new_row["face_hash"] = face_hash
                                try:
                                    resp = supabase.table(TABLE).insert(new_row).execute()
                                except Exception as insert_err:
                                    err_text = str(insert_err)
                                    missing_cols = []
                                    if face_hash and ("face_data" in err_text or "face_hash" in err_text
                                                       or "column" in err_text.lower()):
                                        missing_cols += ["face_data", "face_hash"]
                                    if "blood_type" in err_text or "column" in err_text.lower():
                                        missing_cols.append("blood_type")
                                    if "language" in err_text or "column" in err_text.lower():
                                        missing_cols.append("language")
                                    if missing_cols:
                                        for col in set(missing_cols):
                                            new_row.pop(col, None)
                                        resp = supabase.table(TABLE).insert(new_row).execute()
                                        st.warning(tr("register_warning_missing_cols"))
                                    else:
                                        raise
                                if resp.data:
                                    load_profile_into_session(resp.data[0])
                                    # Đảm bảo giao diện đổi ngôn ngữ NGAY LẬP TỨC sau khi đăng ký, kể cả
                                    # khi cột 'language' chưa tồn tại trên Supabase (insert phía trên đã
                                    # tự bỏ cột đó) — vẫn áp dụng lựa chọn của người dùng trong phiên này.
                                    st.session_state.language = r_language
                                    st.session_state.med_data = []
                                    st.success(tr("register_success"))
                                    st.rerun()
                            except Exception as db_err:
                                err_msg = str(db_err)
                                if "duplicate key" in err_msg or "23505" in err_msg:
                                    st.error(tr("register_error_exists", phone=r_phone_clean))
                                else:
                                    st.error(f"{tr('register_error_db')} {db_err}")
    st.caption(tr("disclaimer"))
# =====================================================================================
# MÀN HÌNH 3: DASHBOARD CHÍNH
# =====================================================================================
else:
    reset_daily_adherence_state_if_needed()

    detected_conflicts = scan_cabinet_for_conflicts(st.session_state.med_data)
    due_family_reminders = fetch_due_family_reminders(st.session_state.user_phone)
    pending_family_invites = fetch_pending_invites_for_member(st.session_state.user_phone)
    with st.sidebar:
        render_app_logo(width=60)
        st.title("SafePill")
        st.caption(f"{tr('sidebar_hello')}: **{st.session_state.current_profile.get('full_name', '')}**")
        st.caption(f"{tr('sidebar_phone')}: `{st.session_state.user_phone}`")
        blood_display = st.session_state.current_profile.get("blood_type")
        if blood_display and blood_display != "Chưa rõ":
            st.caption(f"{tr('sidebar_blood')}: **{blood_display}**")
        st.divider()
        st.subheader(tr("sidebar_adherence"))
        if st.session_state.med_data:
            total_tasks = len(st.session_state.med_data)
            done_tasks = sum(1 for v in st.session_state.adherence_logs.values() if v)
            rate = int((done_tasks / total_tasks) * 100) if total_tasks else 0
            st.progress(rate / 100)
            st.metric(tr("sidebar_taken_today"), f"{rate}%")
        else:
            st.info(tr("sidebar_no_schedule"))
        if pending_family_invites:
            st.divider()
            st.warning(tr("sidebar_pending_invites", n=len(pending_family_invites)))
        st.divider()
        st.session_state.elderly_mode = st.toggle(tr("sidebar_elderly_toggle"),
                                                    value=st.session_state.elderly_mode)
        if st.button(tr("sidebar_logout")):
            for key, default_val in DEFAULT_STATE.items():
                st.session_state[key] = default_val() if callable(default_val) else default_val
            st.session_state.onboarded = True
            st.rerun()

    # ---- CSS cố định để thanh tab luôn hiện đủ icon + chữ, không bị cắt mất chữ ----
    st.markdown(
        """
        <style>
        [data-baseweb="tab-list"] {
            overflow-x: auto !important;
            flex-wrap: nowrap !important;
        }
        [data-baseweb="tab"] {
            white-space: nowrap !important;
            min-width: fit-content !important;
            flex-shrink: 0 !important;
        }
        [data-baseweb="tab"] p {
            white-space: nowrap !important;
            overflow: visible !important;
            text-overflow: unset !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state.elderly_mode:
        # Lưu ý: KHÔNG áp font-size lớn lên nút tab (button trong [data-baseweb="tab"]),
        # vì 8 tab không đủ chỗ hiển thị chữ ở cỡ 22px trên màn hình nhỏ -> chữ bị ẩn,
        # chỉ còn icon. Nút "Taken/Missed" v.v. bên trong nội dung vẫn được phóng to bình thường.
        st.markdown(
            "<style> p,span,label,h3,h2,input,li {font-size:22px !important;} "
            "button:not([data-baseweb='tab']) {font-size:22px !important;} "
            "th,td {font-size:19px !important;} </style>",
            unsafe_allow_html=True,
        )

    st.title(tr("dashboard_title"))
    st.caption(tr("disclaimer"))

    m1, m2, m3 = st.columns(3)
    m1.metric(tr("metric_med_count"), f"{len(st.session_state.med_data)}")
    if detected_conflicts:
        m2.metric(tr("metric_interaction"), tr("metric_interaction_alert"),
                   delta=tr("metric_interaction_alert_delta"), delta_color="inverse")
    else:
        m2.metric(tr("metric_interaction"), tr("metric_interaction_safe"),
                   delta=tr("metric_interaction_safe_delta"))
    med_data_valid = [m for m in st.session_state.med_data if m.get("Tên thuốc")]
    todays_reminders = len(med_data_valid)
    m3.metric(tr("metric_schedule"), f"{todays_reminders} {tr('metric_schedule_unit')}")

    st.divider()
    tab_home, tab_ocr, tab_cabinet, tab_matrix, tab_expert, tab_report, tab_qr, tab_settings = st.tabs([
        tr("tab_home"), tr("tab_ocr"), tr("tab_cabinet"), tr("tab_matrix"),
        tr("tab_expert"), tr("tab_report"), tr("tab_qr"), tr("tab_settings"),
    ])

    # ---------------- TAB HÔM NAY: nhắc nhở theo giờ ----------------
    with tab_home:
        st.header(tr("home_header"))

        # ---- MỚI: nút kích hoạt thông báo + âm thanh, PHẢI gắn trực tiếp vào 1 lần bấm
        # của người dùng để hoạt động trên mobile. KHÔNG tự động gọi requestPermission(),
        # vì trình duyệt mobile sẽ âm thầm từ chối nếu không có user gesture trực tiếp. ----
        _sound_js_fn_top = build_reminder_sound_script(
            st.session_state.reminder_sound, st.session_state.reminder_volume
        )
        _enable_notif_html = f"""
        <button id="enableNotifBtn" style="padding:10px 18px;border-radius:10px;border:none;
        background:#006a62;color:white;cursor:pointer;font-size:15px;width:100%;
        font-weight:600;">{tr('notif_enable_btn')}</button>
        <p id="notifStatusMsg" style="font-size:13px;color:#666;margin-top:6px;"></p>
        <script>
        {_sound_js_fn_top}
        document.getElementById('enableNotifBtn').addEventListener('click', function() {{
            try {{ playReminderSound("{st.session_state.reminder_sound}", {st.session_state.reminder_volume}); }} catch(e) {{}}
            var statusEl = document.getElementById('notifStatusMsg');
            if (window.Notification) {{
                Notification.requestPermission().then(function(perm) {{
                    if (perm === "granted") {{
                        statusEl.innerText = "{tr('notif_permission_granted')}";
                        try {{
                            new Notification("{tr('home_notification_title')}", {{ body: "{tr('notif_permission_granted')}" }});
                        }} catch(e) {{}}
                    }} else {{
                        statusEl.innerText = "{tr('notif_permission_denied')}";
                    }}
                }});
            }} else {{
                statusEl.innerText = "{tr('notif_not_supported')}";
            }}
        }});
        </script>
        """
        components.html(_enable_notif_html, height=90)

        # ---- Banner nổi bật "Add to Home Screen" cho iPhone/iPad, chỉ tự hiện khi thiết bị
        # thực sự là iOS Safari và CHƯA chạy ở chế độ standalone (đã cài vào MH chính).
        # Việc hiện/ẩn xử lý hoàn toàn ở phía client (JS), không cần round-trip Streamlit. ----
        _ios_title_js = json.dumps(tr("notif_ios_add_home_title"), ensure_ascii=False)
        _ios_step1_js = json.dumps(tr("notif_ios_add_home_step1"), ensure_ascii=False)
        _ios_step2_js = json.dumps(tr("notif_ios_add_home_step2"), ensure_ascii=False)
        _ios_step3_js = json.dumps(tr("notif_ios_add_home_step3"), ensure_ascii=False)
        _ios_note_js = json.dumps(tr("notif_ios_add_home_note"), ensure_ascii=False)
        components.html(f"""
        <div id="iosAddHomeBanner" style="display:none;background:linear-gradient(135deg,#fff7ed,#ffedd5);
        border:2px solid #f59e0b;border-radius:12px;padding:14px 16px;margin-top:4px;">
            <p style="margin:0 0 8px 0;font-weight:700;color:#92400e;font-size:15px;"></p>
            <p id="iosStep1" style="margin:2px 0;color:#78350f;font-size:14px;"></p>
            <p id="iosStep2" style="margin:2px 0;color:#78350f;font-size:14px;"></p>
            <p id="iosStep3" style="margin:2px 0 8px 0;color:#78350f;font-size:14px;"></p>
            <p id="iosNote" style="margin:0;color:#92400e;font-size:12.5px;font-style:italic;"></p>
        </div>
        <script>
        (function() {{
            var ua = navigator.userAgent || navigator.vendor || window.opera;
            var isIOS = /iPad|iPhone|iPod/.test(ua) && !window.MSStream;
            // Một số iPadOS mới báo UA giống macOS nhưng có touch -> kiểm tra thêm
            var isIPadOS13Up = navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1;
            var isStandalone = window.navigator.standalone === true ||
                window.matchMedia('(display-mode: standalone)').matches;
            if ((isIOS || isIPadOS13Up) && !isStandalone) {{
                document.getElementById('iosAddHomeBanner').style.display = 'block';
                document.querySelector('#iosAddHomeBanner p').innerText = {_ios_title_js};
                document.getElementById('iosStep1').innerText = {_ios_step1_js};
                document.getElementById('iosStep2').innerText = {_ios_step2_js};
                document.getElementById('iosStep3').innerText = {_ios_step3_js};
                document.getElementById('iosNote').innerText = {_ios_note_js};
            }}
        }})();
        </script>
        """, height=190)
        st.divider()

        if AUTOREFRESH_AVAILABLE:
            st_autorefresh(interval=60_000, key="home_overdue_autorefresh")

        auto_escalated_now = check_and_auto_escalate_overdue_doses(med_data_valid)
        if auto_escalated_now:
            for item in auto_escalated_now:
                if item["sent_to"] > 0:
                    st.error(tr("home_auto_escalate_msg", mins=AUTO_ESCALATION_MINUTES,
                                 time=item['time'], drug=item['drug'], n=item['sent_to']))
                else:
                    st.error(tr("home_auto_escalate_msg_no_family", mins=AUTO_ESCALATION_MINUTES,
                                 time=item['time'], drug=item['drug']))
                
        with st.expander(tr("home_custom_expander"), expanded=False):
            st.caption(tr("home_custom_caption"))
            with st.form("add_custom_reminder_form", clear_on_submit=True):
                rc1, rc2 = st.columns([3, 2])
                custom_label = rc1.text_input(tr("home_custom_label_input"),
                                               placeholder=tr("home_custom_label_placeholder"))
                custom_time = rc2.time_input(tr("home_custom_time_input"), value=dtime(8, 0))
                submit_custom = st.form_submit_button(tr("home_custom_add_btn"))
                if submit_custom:
                    if not custom_label.strip():
                        st.warning(tr("home_custom_warn_empty"))
                    else:
                        st.session_state.custom_reminders.append({
                            "label": custom_label.strip(),
                            "time": custom_time.strftime("%H:%M"),
                        })
                        st.success(tr("home_custom_added"))
                        st.rerun()

            if st.session_state.custom_reminders:
                st.markdown(tr("home_custom_list_title"))
                for cidx, cr in enumerate(list(st.session_state.custom_reminders)):
                    ccols = st.columns([1, 3, 1])
                    ccols[0].markdown(f"**{cr['time']}**")
                    ccols[1].markdown(cr["label"])
                    if ccols[2].button("🗑️", key=f"del_custom_{cidx}"):
                        st.session_state.custom_reminders.pop(cidx)
                        st.rerun()
            else:
                st.caption(tr("home_custom_none"))

        st.divider()

        family_reminder_payload = []
        if due_family_reminders:
            st.markdown(tr("home_family_reminder_title"))
            for fr in due_family_reminders:
                sender = fr.get("sender_name") or fr.get("sender_phone") or tr("home_family_reminder_default_sender")
                st.warning(f"**{sender}** {tr('home_family_reminder_prefix')} {fr.get('message', '')}")
                family_reminder_payload.append({
                    "name": f"{sender} {tr('home_family_reminder_prefix')} {fr.get('message', '')}",
                    "time": datetime.now().strftime("%H:%M"),
                })
                mark_family_reminder_delivered(fr.get("id"))
            st.divider()

        if not med_data_valid and not st.session_state.custom_reminders and not family_reminder_payload:
            st.info(tr("home_empty"))
        else:
            reminder_payload = list(family_reminder_payload)

            if med_data_valid:
                schedule = sorted(
                    med_data_valid,
                    key=lambda m: resolve_reminder_time(m.get("Thời điểm", "")),
                )
                for med in schedule:
                    hhmm = resolve_reminder_time(med.get("Thời điểm", ""))
                    key_name = build_adherence_task_key(med.get("Tên thuốc"), hhmm, med)
                    taken = st.session_state.adherence_logs.get(key_name, False)
                    real_idx = next((i for i, m in enumerate(st.session_state.med_data) if m is med), None)
                    if st.session_state.tts_enabled:
                        cols = st.columns([1, 3, 2, 1.3, 1.3, 1.3])
                    else:
                        cols = st.columns([1, 3, 2, 1.3, 1.3])
                    cols[0].markdown(f"**{hhmm}**")
                    pill_icon = render_pill_icon_html(med.get("Màu sắc", ""), med.get("Hình dạng", ""))
                    cols[1].markdown(
                        f"{pill_icon} **{med.get('Tên thuốc', '')}** — {med.get('Liều lượng', '')}",
                        unsafe_allow_html=True,
                    )
                    note = med.get("Lời dặn", "")
                    if note:
                        cols[1].caption(f"{tr('cabinet_note_prefix')} {note}")
                    cols[2].markdown(f"_{med.get('Thời điểm', '')}_")
                    checked = cols[3].checkbox(tr("home_taken_checkbox"), value=taken, key=f"checked_{key_name}")
                    missed_clicked = cols[4].button(tr("home_missed_btn"), key=f"missed_{key_name}")
                    if st.session_state.tts_enabled:
                        with cols[5]:
                            components.html(
                                build_tts_button_html(
                                    f"{tr('tts_read_aloud_prefix')} {med.get('Tên thuốc','')}, "
                                    f"{tr('tts_read_aloud_dose')} {med.get('Liều lượng','')}, "
                                    f"{tr('tts_read_aloud_at')} {med.get('Thời điểm','')}",
                                    button_label=tr("tts_read_aloud").split(" ")[0], key_suffix=key_name,
                                ), height=42,
                            )
                    if checked != taken:
                        st.session_state.adherence_logs[key_name] = checked
                        if checked:
                            reset_missed_dose(med.get("Tên thuốc", ""))
                            if real_idx is not None:
                                decrement_med_quantity(real_idx, key_name)
                        else:
                            if real_idx is not None:
                                restore_med_quantity(real_idx, key_name)
                        save_med_data_to_supabase()
                        st.rerun()
                    if missed_clicked:
                        st.session_state.adherence_logs[key_name] = False
                        drug_name = med.get("Tên thuốc", "")
                        severity = get_missed_dose_severity(drug_name)
                        streak = record_missed_dose(drug_name, severity=severity)
                        st.warning(tr("home_missed_recorded", drug=drug_name, n=streak))
                        if streak >= 2 and severity in ("Cao", "Nghiêm trọng"):
                                sent_to = send_escalation_alert_to_family(
                                st.session_state.user_phone,
                                st.session_state.current_profile.get("full_name", ""),
                                drug_name, streak,
                            )
                        if sent_to:
                            st.error(tr("home_missed_escalated", n=len(sent_to),
                                severity=severity, streak=streak))
                        st.rerun()
                    qty_left = med.get("Số lượng còn lại")
                    if qty_left is not None:
                        try:
                            if int(qty_left) <= LOW_STOCK_THRESHOLD:
                                st.warning(tr("home_low_stock", drug=med.get('Tên thuốc',''), qty=qty_left))
                        except (TypeError, ValueError):
                            pass
                    reminder_payload.append({"name": med.get("Tên thuốc", ""), "time": hhmm})

            if st.session_state.custom_reminders:
                st.markdown(tr("home_custom_today_title"))
                for cr in sorted(st.session_state.custom_reminders, key=lambda x: x["time"]):
                    st.markdown(f"- ⏰ **{cr['time']}** — {cr['label']}")
                    reminder_payload.append({"name": cr["label"], "time": cr["time"]})

            st.divider()
            st.caption(tr("home_notification_caption"))
            reminder_json = json.dumps(reminder_payload, ensure_ascii=False)
            sound_type = st.session_state.reminder_sound
            sound_volume = st.session_state.reminder_volume
            sound_js_fn = build_reminder_sound_script(sound_type, sound_volume)
            notif_title_js = json.dumps(tr("home_notification_title"), ensure_ascii=False)
            notif_body_suffix_js = json.dumps(f" {tr('home_notification_body_suffix')}", ensure_ascii=False)
            components.html(f"""
            <script>
            const meds = {reminder_json};
            const soundType = "{sound_type}";
            const soundVolume = {sound_volume};
            {sound_js_fn}
            function checkReminders() {{
                const now = new Date();
                const hhmm = String(now.getHours()).padStart(2,'0') + ":" + String(now.getMinutes()).padStart(2,'0');
                meds.forEach(m => {{
                    if (m.time === hhmm) {{
                        if (window.Notification && Notification.permission === "granted") {{
                            new Notification({notif_title_js}, {{ body: m.name + {notif_body_suffix_js} }});
                        }}
                        playReminderSound(soundType, soundVolume);
                    }}
                }});
            }}
            setInterval(checkReminders, 30000);
            </script>
            """, height=0)
            st.divider()
            if detected_conflicts:
                st.error(tr("home_conflict_warning"))
                st.toast(tr("home_conflict_warning"), icon="🚨")

    # ---------------- TAB QUÉT ĐƠN THUỐC (Vision AI) ----------------
    with tab_ocr:
        st.header(tr("ocr_header"))
        st.info(tr("ocr_info"))

        st.markdown(tr("ocr_clinic_section_title"))
        st.caption(tr("ocr_clinic_section_caption"))
        rx_col1, rx_col2, rx_col3 = st.columns(3)
        rx_clinic = rx_col1.text_input(
            tr("ocr_clinic_label"), placeholder=tr("ocr_clinic_placeholder"), key="rx_common_clinic",
        )
        rx_doctor = rx_col2.text_input(
            tr("ocr_doctor_label"), placeholder=tr("ocr_doctor_placeholder"), key="rx_common_doctor",
        )
        rx_pharmacy = rx_col3.text_input(
            tr("ocr_pharmacy_label"), placeholder=tr("ocr_pharmacy_placeholder"), key="rx_common_pharmacy",
        )
        st.divider()

        PRESCRIPTION_VISION_PROMPT = """
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
        "Nơi cấp thuốc": "tên nhà thuốc/quầy thuốc cấp phát (để trống nếu không thấy)"
        "Lời dặn": "lời dặn của bác sĩ ghi trên đơn, ví dụ: uống sau khi ăn, tránh nắng, không dùng chung với rượu (để trống nếu không thấy)"
    }
]
Nếu chữ viết khó đọc, hãy suy luận hợp lý dựa trên bao bì hoặc tên thuốc phổ biến.
Trường "Màu sắc" và "Hình dạng" giúp người già không đọc được chữ nhỏ vẫn nhận diện được thuốc qua hình ảnh minh hoạ.
Các trường "Nơi khám bệnh", "Bác sĩ điều trị", "Nơi cấp thuốc" thường lặp lại giống nhau cho mọi loại
thuốc trong CÙNG một đơn/toa — nếu đơn chỉ ghi thông tin này một lần ở đầu hoặc cuối trang, hãy áp dụng
lại giá trị đó cho TẤT CẢ các thuốc được bóc tách từ đơn đó.
Nếu ảnh không chứa thông tin đơn thuốc/thuốc nào, hãy trả về mảng JSON rỗng: []
"""

    def analyze_prescription_image(pil_img, clinic_override: str, doctor_override: str,
                                pharmacy_override: str):
        try:
            response = ai_gemini.models.generate_content(
                model="gemini-flash-latest",
                contents=[pil_img, PRESCRIPTION_VISION_PROMPT],
            )
            parsed_meds = extract_json_array(response.text)
            if not isinstance(parsed_meds, list):
                raise ValueError("AI không trả về danh sách thuốc hợp lệ.")
        except Exception as gemini_err:
                # Gemini API lỗi (quota, timeout, mất kết nối tới Google...) -> tự động
                # chuyển sang OpenVINO chạy ngầm trên máy chủ, không cần người dùng chọn gì.
            try:
                buf = io.BytesIO()
                pil_img.save(buf, format="PNG")
                raw_text = run_openvino_ocr(buf.getvalue())
                parsed_meds = parse_offline_ocr_text(raw_text)
                if not parsed_meds:
                    raise gemini_err  # cả 2 engine đều không ra kết quả -> báo lỗi gốc
            except Exception as openvino_err:
                raise gemini_err  # cả 2 engine đều không ra kết quả -> báo lỗi gốc

        for pm in parsed_meds:
            if clinic_override.strip():
                pm["Nơi khám bệnh"] = clinic_override.strip()
            if doctor_override.strip():
                pm["Bác sĩ điều trị"] = doctor_override.strip()
            if pharmacy_override.strip():
                pm["Nơi cấp thuốc"] = pharmacy_override.strip()
        return parsed_meds
    has_prescription = st.radio(
            tr("ocr_method_label"),
            [tr("ocr_method_camera"), tr("ocr_method_upload"), tr("ocr_method_manual")],
            horizontal=False,
        )

    if has_prescription == tr("ocr_method_camera"):
            img_file = st.camera_input(tr("ocr_camera_capture"), key="clinical_vision_cam")
            if img_file:
                with st.spinner(tr("ocr_analyzing")):
                    try:
                        pil_img = Image.open(io.BytesIO(img_file.getvalue()))
                        parsed_meds = analyze_prescription_image(pil_img, rx_clinic, rx_doctor, rx_pharmacy)
                        if not parsed_meds:
                            st.warning(tr("ocr_no_meds_found"))
                        else:
                            st.session_state.med_data.extend(parsed_meds)
                            save_med_data_to_supabase()
                            st.success(tr("ocr_added_success", n=len(parsed_meds)))
                            st.rerun()
                    except Exception as ex:
                        st.error(f"{tr('ocr_analyze_fail')} {ex}")
                        st.caption(tr("ocr_analyze_fail_hint"))
            manual_expanded = False
            manual_title = tr("ocr_manual_expander")

    elif has_prescription == tr("ocr_method_upload"):
            uploaded_files = st.file_uploader(
                tr("ocr_upload_label"),
                type=["png", "jpg", "jpeg", "webp"],
                accept_multiple_files=True,
                key="clinical_vision_upload",
            )
            if uploaded_files:
                st.caption(tr("ocr_upload_selected", n=len(uploaded_files)))
                preview_cols = st.columns(min(len(uploaded_files), 4))
                for i, uf in enumerate(uploaded_files):
                    with preview_cols[i % len(preview_cols)]:
                        st.image(uf, use_container_width=True, caption=uf.name)
                if st.button(tr("ocr_analyze_all_btn"), type="primary", use_container_width=True,
                             key="analyze_uploaded_btn"):
                    all_parsed = []
                    failed_files = []
                    with st.spinner(tr("ocr_analyzing_multi", n=len(uploaded_files))):
                        for uf in uploaded_files:
                            try:
                                pil_img = Image.open(io.BytesIO(uf.getvalue()))
                                parsed_meds = analyze_prescription_image(
                                    pil_img, rx_clinic, rx_doctor, rx_pharmacy
                                )
                                all_parsed.extend(parsed_meds)
                            except Exception as ex:
                                failed_files.append((uf.name, str(ex)))
                    if all_parsed:
                        st.session_state.med_data.extend(all_parsed)
                        save_med_data_to_supabase()
                        st.success(tr("ocr_added_multi_success", n=len(all_parsed), files=len(uploaded_files)))
                    if failed_files:
                        for fname, err in failed_files:
                            st.error(f"{tr('ocr_failed_file', name=fname)} {err}")
                    if not all_parsed and not failed_files:
                        st.warning(tr("ocr_no_meds_multi"))
                    if all_parsed:
                        st.rerun()
            manual_expanded = False
            manual_title = tr("ocr_manual_expander")

    else:
            st.success(tr("ocr_manual_only_success"))
            manual_expanded = True
            manual_title = tr("ocr_manual_title")

    with st.expander(manual_title, expanded=manual_expanded):
            with st.form("manual_add_form", clear_on_submit=True):
                mc1, mc2, mc3, mc4 = st.columns(4)
                man_name = mc1.text_input(tr("ocr_manual_name"))
                man_dose = mc2.text_input(tr("ocr_manual_dose"), value="1 viên")
                time_options = [tr("time_morning"), tr("time_noon"), tr("time_afternoon"), tr("time_evening")]
                man_time = mc3.selectbox(tr("ocr_manual_time"), time_options)
                man_type = mc4.text_input(tr("ocr_manual_type"))
                mc5, mc6, mc7 = st.columns(3)
                man_color = mc5.text_input(tr("ocr_manual_color"), placeholder=tr("ocr_manual_color_placeholder"))
                shape_options = ["", tr("shape_round"), tr("shape_oval"), tr("shape_tablet"),
                                  tr("shape_square"), tr("shape_capsule")]
                man_shape = mc6.selectbox(tr("ocr_manual_shape"), shape_options)
                man_qty = mc7.number_input(tr("ocr_manual_qty"), min_value=0, value=0, step=1)
                st.markdown(tr("ocr_manual_clinic_section"))
                mc8, mc9, mc10 = st.columns(3)
                man_clinic = mc8.text_input(
                    tr("ocr_clinic_label"), value=rx_clinic, placeholder=tr("ocr_clinic_placeholder"), key="man_clinic",
                )
                man_doctor = mc9.text_input(
                    tr("ocr_doctor_label"), value=rx_doctor, placeholder=tr("ocr_doctor_placeholder"), key="man_doctor",
                )
                man_pharmacy = mc10.text_input(
                    tr("ocr_pharmacy_label"), value=rx_pharmacy, placeholder=tr("ocr_pharmacy_placeholder"), key="man_pharmacy",
                )
                man_note = st.text_area(
                    tr("ocr_manual_note"),
                    placeholder=tr("ocr_manual_note_placeholder"), key="man_note"
                )
                if st.form_submit_button(tr("ocr_manual_submit")):
                    if man_name.strip():
                        new_med_entry = {
                            "Tên thuốc": man_name.strip(), "Liều lượng": man_dose.strip(),
                            "Thời điểm": man_time, "Loại": man_type.strip(),
                            "Màu sắc": man_color.strip(), "Hình dạng": man_shape,
                            "Nơi khám bệnh": man_clinic.strip(),
                            "Bác sĩ điều trị": man_doctor.strip(),
                            "Nơi cấp thuốc": man_pharmacy.strip(),
                            "Lời dặn": man_note.strip(),
                        }
                        if man_qty > 0:
                            new_med_entry["Số lượng còn lại"] = int(man_qty)
                        st.session_state.med_data.append(new_med_entry)
                        save_med_data_to_supabase()
                        st.success(tr("ocr_manual_added"))
                        st.rerun()
                    else:
                        st.warning(tr("ocr_manual_warn_name"))

    # ---------------- TAB TỦ THUỐC SỐ ----------------
    with tab_cabinet:
        st.header(tr("cabinet_header"))
        if detected_conflicts:
            st.error(tr("cabinet_conflict_alert"))
            for c in detected_conflicts:
                st.markdown(f"> **{c['thuoc_1']}** ↔ **{c['thuoc_2']}** \n"
                            f"> {tr('cabinet_severity_label')}: **{loc_field(c, 'severity')}** — {loc_field(c, 'effect')}  \n"
                            f"> _{tr('cabinet_source_label')}: {loc_field(c, 'nguon') or DEFAULT_SOURCE_NOTE}_")
            st.warning(tr("cabinet_consult_warning"))

        food_herb_warnings = check_food_herb_conflicts(st.session_state.med_data)
        if food_herb_warnings:
            st.warning(tr("cabinet_food_warning_title"))
            for w in food_herb_warnings:
                st.markdown(f"> **{w['thuoc']}** ↔ *{loc_field(w, 'item')}* — {tr('cabinet_severity_label')}: **{loc_field(w, 'severity')}**  \n"
                            f"> {loc_field(w, 'effect')}  \n"
                            f"> _{tr('cabinet_source_label')}: {loc_field(w, 'nguon') or DEFAULT_SOURCE_NOTE}_")
            st.caption(tr("cabinet_food_warning_caption"))

        if not med_data_valid:
            st.info(tr("cabinet_empty"))
        else:
            st.subheader(tr("cabinet_list_title"))
            for idx, med in enumerate(list(st.session_state.med_data)):
                cols = st.columns([0.6, 2.4, 2, 2, 1.6, 1.4, 1])
                cols[0].markdown(render_pill_icon_html(med.get("Màu sắc", ""), med.get("Hình dạng", "")),
                                  unsafe_allow_html=True)
                cols[1].markdown(f"**{med.get('Tên thuốc','')}**")
                cols[2].markdown(med.get("Liều lượng", ""))
                cols[3].markdown(med.get("Thời điểm", ""))
                cols[4].markdown(med.get("Loại", ""))
                qty_left = med.get("Số lượng còn lại")
                qty_display = f"{qty_left} {tr('cabinet_qty_unit')}" if qty_left is not None else "—"
                cols[5].markdown(qty_display)
                if cols[6].button("🗑️", key=f"del_{idx}"):
                    st.session_state.med_data.pop(idx)
                    save_med_data_to_supabase()
                    st.rerun()
                clinic = med.get("Nơi khám bệnh", "")
                doctor = med.get("Bác sĩ điều trị", "")
                pharmacy = med.get("Nơi cấp thuốc", "")
                if clinic or doctor or pharmacy:
                    detail_bits = []
                    if clinic:
                        detail_bits.append(f"{tr('cabinet_clinic_prefix')} {clinic}")
                    if doctor:
                        detail_bits.append(f"{tr('cabinet_doctor_prefix')} {doctor}")
                    if pharmacy:
                        detail_bits.append(f"{tr('cabinet_pharmacy_prefix')} {pharmacy}")
                    st.caption(" | ".join(detail_bits))
                    note = med.get("Lời dặn", "")
            if note:
                st.caption(f"{tr('cabinet_note_prefix')} {note}")

    # ---------------- TAB TRA CỨU TƯƠNG TÁC ----------------
    with tab_matrix:
        st.header(tr("matrix_header"))
        st.caption(tr("matrix_caption"))
        col_t1, col_t2 = st.columns(2)
        t1 = col_t1.text_input(tr("matrix_drug_a"), value="Aspirin")
        t2 = col_t2.text_input(tr("matrix_drug_b"), value="Ibuprofen")
        if st.button(tr("matrix_check_btn"), type="primary", use_container_width=True):
            drug_result = check_interaction(t1, t2)
            food_results = check_food_herb_pair(t1, t2)

            if drug_result:
                st.error(tr("matrix_drug_alert", severity=loc_field(drug_result, 'severity')))
                st.markdown(f"- {tr('matrix_drug_pair')} `{drug_result['thuoc_1']}` và `{drug_result['thuoc_2']}`\n"
                            f"- {tr('matrix_effect')} {loc_field(drug_result, 'effect')}\n"
                            f"- {tr('matrix_source')} {loc_field(drug_result, 'nguon') or DEFAULT_SOURCE_NOTE}\n"
                            f"- {tr('matrix_recommendation')} {tr('matrix_recommendation_drug')}")

            if food_results:
                for fr in food_results:
                    st.warning(tr("matrix_food_alert", severity=loc_field(fr, 'severity')))
                    st.markdown(f"- **{fr['thuoc']}** ↔ *{loc_field(fr, 'item')}*\n"
                                f"- {tr('matrix_effect')} {loc_field(fr, 'effect')}\n"
                                f"- {tr('matrix_source')} {loc_field(fr, 'nguon') or DEFAULT_SOURCE_NOTE}\n"
                                f"- {tr('matrix_recommendation')} {tr('matrix_recommendation_food')}")

            if not drug_result and not food_results:
                st.success(tr("matrix_safe", a=t1.strip().capitalize(), b=t2.strip().capitalize()))
        st.caption(tr("matrix_footer_caption"))

    # ---------------- TAB HỎI ĐÁP AI ----------------
    with tab_expert:
        st.header(tr("expert_header"))
        st.caption(tr("disclaimer"))
        st.caption(tr("expert_grounding_caption"))
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        user_query = st.chat_input(tr("expert_chat_placeholder"))
        if user_query:
            st.session_state.chat_history.append({"role": "user", "content": user_query})
            with st.chat_message("user"):
                st.markdown(user_query)
            with st.chat_message("assistant"):
                with st.spinner(tr("expert_analyzing")):
                    try:
                        # ---- MỚI: chỉ định rõ ngôn ngữ trả lời cho Gemini theo lựa chọn hiện tại ----
                        full_prompt = f"""
Bạn là trợ lý dược sĩ AI của ứng dụng SafePill. Luôn nhắc người dùng đây là thông tin tham khảo,
không thay thế chỉ định của bác sĩ, và đề nghị đi khám nếu triệu chứng nghiêm trọng hoặc kéo dài.
Khi trả lời về liều dùng, tác dụng phụ hoặc tương tác thuốc, ƯU TIÊN đối chiếu các nguồn uy tín như
Drugs.com, Dược thư Quốc gia Việt Nam, MedlinePlus, hoặc các bệnh viện/tổ chức y tế lớn (Mayo Clinic,
Bệnh viện Bạch Mai, Bệnh viện Chợ Rẫy...) để đảm bảo thông tin chính xác nhất có thể.
Thông tin bệnh nhân: {st.session_state.current_profile.get('full_name', tr('expert_anon_name'))}.
Tủ thuốc hiện tại: {st.session_state.med_data}.
Tương tác đã phát hiện: {detected_conflicts}.
Câu hỏi: '{user_query}'.
QUAN TRỌNG: hãy trả lời bằng {current_lang_name()}. {tr('expert_lang_instruction')}
"""
                        if GEMINI_SEARCH_GROUNDING_AVAILABLE:
                            try:
                                response = ai_gemini.models.generate_content(
                                    model="gemini-flash-latest",
                                    contents=full_prompt,
                                    config=genai_types.GenerateContentConfig(
                                        tools=[genai_types.Tool(google_search=genai_types.GoogleSearch())]
                                    ),
                                )
                            except Exception:
                                response = ai_gemini.models.generate_content(
                                    model="gemini-flash-latest", contents=full_prompt,
                                )
                        else:
                            response = ai_gemini.models.generate_content(
                                model="gemini-flash-latest", contents=full_prompt,
                            )
                        ai_response = response.text or ""

                        source_links = []
                        try:
                            candidate = response.candidates[0]
                            grounding = getattr(candidate, "grounding_metadata", None)
                            chunks = getattr(grounding, "grounding_chunks", None) if grounding else None
                            if chunks:
                                for chunk in chunks:
                                    web_info = getattr(chunk, "web", None)
                                    if web_info and getattr(web_info, "uri", None):
                                        title = getattr(web_info, "title", None) or web_info.uri
                                        source_links.append((title, web_info.uri))
                        except Exception:
                            source_links = []

                        if source_links:
                            ai_response += tr("expert_sources_title")
                            seen_uris = set()
                            for title, uri in source_links:
                                if uri in seen_uris:
                                    continue
                                seen_uris.add(uri)
                                ai_response += f"- [{title}]({uri})\n"

                        st.markdown(ai_response)
                        st.session_state.chat_history.append({"role": "assistant", "content": ai_response})
                    except Exception as e:
                        st.error(f"{tr('expert_error')} {e}")

    # ---------------- TAB BÁO CÁO TUÂN THỦ ----------------
    with tab_report:
        st.header(tr("report_header"))
        st.caption(tr("report_caption"))

        total_tasks_today = len(med_data_valid)
        done_tasks_today = sum(1 for v in st.session_state.adherence_logs.values() if v)

        rc1, rc2 = st.columns([2, 1])
        rc1.metric(tr("report_today_rate"),
                    f"{int((done_tasks_today/total_tasks_today)*100) if total_tasks_today else 0}%")
        if rc2.button(tr("report_save_btn"), use_container_width=True):
            if total_tasks_today == 0:
                st.warning(tr("report_no_schedule_warn"))
            else:
                ok, err = log_adherence_snapshot(st.session_state.user_phone, total_tasks_today, done_tasks_today)
                if ok:
                    st.session_state.adherence_logged_today = True
                    st.success(tr("report_save_success"))
                else:
                    st.error(ADHERENCE_HISTORY_MISSING_MSG if _is_missing_table_error(err)
                              else f"{tr('family_send_error')} {err}")

        st.divider()
        st.subheader(tr("report_chart_title"))
        history_rows = fetch_adherence_history(st.session_state.user_phone, days=30)
        if not history_rows:
            st.info(tr("report_no_history"))
        elif not MATPLOTLIB_AVAILABLE:
            st.warning(tr("report_no_matplotlib"))
            st.table(history_rows)
        else:
            dates = [r["log_date"] for r in history_rows]
            rates = [float(r.get("rate", 0)) for r in history_rows]
            fig, ax = plt.subplots(figsize=(9, 4))
            ax.plot(dates, rates, marker="o", color="#006a62", linewidth=2)
            ax.set_ylim(0, 105)
            ax.set_ylabel(tr("report_chart_ylabel"))
            ax.set_xlabel(tr("report_chart_xlabel"))
            ax.set_title(f"{tr('report_chart_title_prefix')} {st.session_state.current_profile.get('full_name','')}")
            ax.grid(True, alpha=0.3)
            plt.xticks(rotation=45, ha="right")
            fig.tight_layout()
            st.pyplot(fig)

            pdf_buffer = io.BytesIO()
            fig.savefig(pdf_buffer, format="pdf")
            pdf_buffer.seek(0)
            png_buffer = io.BytesIO()
            fig.savefig(png_buffer, format="png", dpi=150)
            png_buffer.seek(0)
            dl1, dl2 = st.columns(2)
            dl1.download_button(tr("report_download_pdf"), data=pdf_buffer,
                                  file_name=f"bao_cao_tuan_thu_{st.session_state.user_phone}.pdf",
                                  mime="application/pdf", use_container_width=True)
            dl2.download_button(tr("report_download_png"), data=png_buffer,
                                  file_name=f"bao_cao_tuan_thu_{st.session_state.user_phone}.png",
                                  mime="image/png", use_container_width=True)
            plt.close(fig)
            st.caption(tr("report_bring_to_doctor"))

    # ---------------- TAB THẺ QR KHẨN CẤP ----------------
    with tab_qr:
        st.header(tr("qr_header"))
        st.info(tr("qr_info"))
        family_members_for_qr = fetch_family_members(st.session_state.user_phone)
        qr_text = build_emergency_qr_text(
            st.session_state.current_profile, st.session_state.med_data,
            detected_conflicts, family_members_for_qr,
        )
        if not QRCODE_AVAILABLE:
            st.warning(tr("qr_no_library"))
        else:
            qr_img = generate_qr_image(qr_text)
            qcol1, qcol2 = st.columns([1, 1.4])
            with qcol1:
                st.image(qr_img, caption=tr("qr_image_caption"), width=280)
                qr_buf = io.BytesIO()
                qr_img.save(qr_buf, format="PNG")
                qr_buf.seek(0)
                st.download_button(tr("qr_download_btn"), data=qr_buf,
                                     file_name=f"safepill_qr_khan_cap_{st.session_state.user_phone}.png",
                                     mime="image/png", use_container_width=True)
            with qcol2:
                st.markdown(tr("qr_content_title"))
                st.code(qr_text, language=None)

            st.divider()
            st.subheader(tr("qr_wallpaper_title"))
            st.info(tr("qr_wallpaper_info"))
            size_choice = st.selectbox(tr("qr_size_select"), list(WALLPAPER_SIZES.keys()))
            wallpaper_img = generate_lockscreen_wallpaper(
                qr_img, st.session_state.current_profile, detected_conflicts, size_choice
            )
            wcol1, wcol2 = st.columns([1, 1.4])
            with wcol1:
                st.image(wallpaper_img, caption=tr("qr_wallpaper_preview_caption"), width=260)
                wallpaper_buf = io.BytesIO()
                wallpaper_img.save(wallpaper_buf, format="PNG")
                wallpaper_buf.seek(0)
                st.download_button(
                    tr("qr_wallpaper_download"), data=wallpaper_buf,
                    file_name=f"safepill_lockscreen_{st.session_state.user_phone}.png",
                    mime="image/png", use_container_width=True, type="primary",
                )
            with wcol2:
                st.markdown(tr("qr_wallpaper_howto_title"))
        st.caption(tr("qr_footer_caption"))

    # ---------------- TAB CÀI ĐẶT ----------------
    with tab_settings:
        st.header(tr("settings_header"))
        sub_account, sub_schedule, sub_notification, sub_family = st.tabs([
            tr("settings_sub_account"), tr("settings_sub_schedule"),
            tr("settings_sub_notification"), tr("settings_sub_family"),
        ])

        # ===== TÀI KHOẢN =====
        with sub_account:
            st.subheader(tr("acc_personal_info"))
            with st.form("update_profile_form"):
                new_name = st.text_input(
                    tr("acc_full_name"),
                    value=st.session_state.current_profile.get("full_name", ""),
                )
                current_blood = st.session_state.current_profile.get("blood_type") or "Chưa rõ"
                new_blood_type = st.selectbox(
                    tr("acc_blood_type"),
                    BLOOD_TYPE_OPTIONS,
                    index=BLOOD_TYPE_OPTIONS.index(current_blood) if current_blood in BLOOD_TYPE_OPTIONS else 0,
                )
                # ---- MỚI: đổi ngôn ngữ hiển thị trong Cài đặt ----
                current_lang = st.session_state.get("language", "vi")
                new_language = st.selectbox(
                    tr("acc_language"), options=list(LANGUAGE_OPTIONS.keys()),
                    format_func=lambda k: LANGUAGE_OPTIONS[k],
                    index=list(LANGUAGE_OPTIONS.keys()).index(current_lang),
                )
                submit_name = st.form_submit_button(tr("acc_save_btn"))
                if submit_name:
                    if not new_name.strip():
                        st.error(tr("acc_error_empty_name"))
                    else:
                        try:
                            try:
                                supabase.table(TABLE).update({
                                    "full_name": new_name.strip(), "blood_type": new_blood_type,
                                    "language": new_language,
                                }).eq("phone", st.session_state.user_phone).execute()
                            except Exception as update_err:
                                if ("blood_type" in str(update_err) or "language" in str(update_err)
                                        or "column" in str(update_err).lower()):
                                    supabase.table(TABLE).update({"full_name": new_name.strip()}).eq(
                                        "phone", st.session_state.user_phone
                                    ).execute()
                                    st.warning(tr("acc_missing_col_warn"))
                                else:
                                    raise
                            st.session_state.current_profile["full_name"] = new_name.strip()
                            st.session_state.current_profile["blood_type"] = new_blood_type
                            st.session_state.current_profile["language"] = new_language
                            st.session_state.language = new_language
                            st.success(tr("acc_update_success"))
                            st.rerun()
                        except Exception as e:
                            st.error(f"{tr('acc_update_error')} {e}")

            st.divider()
            st.subheader(tr("acc_change_pin"))
            with st.form("change_pin_form", clear_on_submit=True):
                old_pin = st.text_input(tr("acc_current_pin"), type="password", max_chars=4)
                new_pin = st.text_input(tr("acc_new_pin"), type="password", max_chars=4)
                confirm_pin = st.text_input(tr("acc_confirm_pin"), type="password", max_chars=4)
                submit_pin = st.form_submit_button(tr("acc_change_pin_btn"))
                if submit_pin:
                    old_pin_clean = old_pin.strip()
                    new_pin_clean = new_pin.strip()
                    confirm_pin_clean = confirm_pin.strip()
                    if not old_pin_clean or not new_pin_clean or not confirm_pin_clean:
                        st.error(tr("acc_pin_error_empty"))
                    elif not verify_pin(old_pin_clean, st.session_state.current_profile.get("pin")):
                        st.error(tr("acc_pin_error_wrong"))
                    elif len(new_pin_clean) != 4 or not new_pin_clean.isdigit():
                        st.error(tr("acc_pin_error_format"))
                    elif new_pin_clean != confirm_pin_clean:
                        st.error(tr("acc_pin_error_mismatch"))
                    else:
                        try:
                            new_hash = hash_pin(new_pin_clean)
                            supabase.table(TABLE).update({"pin": new_hash}).eq(
                                "phone", st.session_state.user_phone
                            ).execute()
                            st.session_state.current_profile["pin"] = new_hash
                            st.success(tr("acc_pin_success"))
                        except Exception as e:
                            st.error(f"{tr('acc_update_error')} {e}")

            st.divider()
            st.subheader(tr("acc_faceid_title"))
            has_face = bool(st.session_state.current_profile.get("face_hash"))
            if has_face:
                st.success(tr("acc_faceid_registered"))
            else:
                st.info(tr("acc_faceid_not_registered"))
            with st.expander(tr("acc_faceid_expander")):
                new_face_img = st.camera_input(tr("acc_faceid_capture"), key="settings_face_cam")
                if new_face_img is not None and st.button(tr("acc_faceid_save_btn"), key="save_face_btn"):
                    try:
                        face_bytes = new_face_img.getvalue()
                        new_face_hash = average_hash(face_bytes)
                        if not new_face_hash:
                            st.error(tr("acc_faceid_bad_image"))
                        else:
                            supabase.table(TABLE).update({
                                "face_data": base64.b64encode(face_bytes).decode("utf-8"),
                                "face_hash": new_face_hash,
                            }).eq("phone", st.session_state.user_phone).execute()
                            st.session_state.current_profile["face_hash"] = new_face_hash
                            st.success(tr("acc_faceid_saved"))
                            st.rerun()
                    except Exception as e:
                        st.error(f"{tr('acc_faceid_save_error')} {e}")
            if has_face:
                if st.button(tr("acc_faceid_remove_btn"), key="remove_face_btn"):
                    try:
                        supabase.table(TABLE).update({"face_data": None, "face_hash": None}).eq(
                            "phone", st.session_state.user_phone
                        ).execute()
                        st.session_state.current_profile["face_hash"] = None
                        st.success(tr("acc_faceid_removed"))
                        st.rerun()
                    except Exception as e:
                        st.error(f"{tr('acc_faceid_remove_error')} {e}")

        # ===== LỊCH UỐNG THUỐC =====
        with sub_schedule:
            st.subheader(tr("sched_title"))
            if not med_data_valid:
                st.info(tr("sched_empty"))
            else:
                for idx, med in enumerate(list(st.session_state.med_data)):
                    med_label = med.get("Tên thuốc") or tr("sched_med_fallback", n=idx + 1)
                    with st.expander(f"💊 {med_label}"):
                        col1, col2 = st.columns(2)
                        new_dose = col1.text_input(
                            tr("sched_dose"), value=med.get("Liều lượng", ""), key=f"sched_dose_{idx}"
                        )
                        default_hhmm = resolve_reminder_time(med.get("Thời điểm", ""))
                        h, mnt = default_hhmm.split(":")
                        default_time_obj = dtime(int(h), int(mnt))
                        new_time = col2.time_input(
                            tr("sched_time"), value=default_time_obj, key=f"sched_time_{idx}"
                        )
                        col3, col4, col5 = st.columns(3)
                        new_color = col3.text_input(
                            tr("sched_color"), value=med.get("Màu sắc", ""), key=f"sched_color_{idx}"
                        )
                        shape_options = ["", tr("shape_round"), tr("shape_oval"), tr("shape_tablet"),
                                          tr("shape_square"), tr("shape_capsule")]
                        current_shape = med.get("Hình dạng")
                        new_shape = col4.selectbox(
                            tr("sched_shape"), shape_options,
                            index=(shape_options.index(current_shape) if current_shape in shape_options else 0),
                            key=f"sched_shape_{idx}",
                        )
                        new_note = col5.text_area(
                            tr("sched_note"),
                            value=med.get("Lời dặn", ""),
                            key=f"sched_note_{idx}"
                        )
                        new_qty = col5.number_input(
                            tr("sched_qty"), min_value=0,
                            value=int(med.get("Số lượng còn lại", 0) or 0), step=1, key=f"sched_qty_{idx}",
                        )
                        col6, col7, col8 = st.columns(3)
                        new_clinic = col6.text_input(
                            tr("sched_clinic"), value=med.get("Nơi khám bệnh", ""), key=f"sched_clinic_{idx}"
                        )
                        new_doctor = col7.text_input(
                            tr("sched_doctor"), value=med.get("Bác sĩ điều trị", ""), key=f"sched_doctor_{idx}"
                        )
                        new_pharmacy = col8.text_input(
                            tr("sched_pharmacy"), value=med.get("Nơi cấp thuốc", ""), key=f"sched_pharmacy_{idx}"
                        )
                        if st.button(tr("sched_save_btn"), key=f"sched_save_{idx}"):
                            st.session_state.med_data[idx]["Liều lượng"] = new_dose
                            st.session_state.med_data[idx]["Thời điểm"] = new_time.strftime("%H:%M")
                            st.session_state.med_data[idx]["Màu sắc"] = new_color
                            st.session_state.med_data[idx]["Hình dạng"] = new_shape
                            st.session_state.med_data[idx]["Số lượng còn lại"] = int(new_qty)
                            st.session_state.med_data[idx]["Nơi khám bệnh"] = new_clinic
                            st.session_state.med_data[idx]["Bác sĩ điều trị"] = new_doctor
                            st.session_state.med_data[idx]["Nơi cấp thuốc"] = new_pharmacy
                            st.session_state.med_data[idx]["Lời dặn"] = new_note.strip()
                            save_med_data_to_supabase()
                            st.success(tr("sched_save_success", med=med_label))
                            st.rerun()
                st.caption(tr("sched_footer_caption"))

        # ===== THÔNG BÁO & ÂM THANH =====
        with sub_notification:
            st.subheader(tr("notif_title"))
            st.caption(tr("notif_caption"))
            sound_options = {"beep": tr("notif_sound_beep"), "chime": tr("notif_sound_chime"),
                              "bell": tr("notif_sound_bell")}
            sound_keys = list(sound_options.keys())
            selected_sound = st.selectbox(
                tr("notif_sound_type"),
                options=sound_keys,
                format_func=lambda x: sound_options[x],
                index=sound_keys.index(st.session_state.reminder_sound),
            )
            selected_volume = st.slider(
                tr("notif_volume"), min_value=0.0, max_value=1.0,
                value=float(st.session_state.reminder_volume), step=0.1,
            )
            if (selected_sound != st.session_state.reminder_sound
                    or selected_volume != st.session_state.reminder_volume):
                st.session_state.reminder_sound = selected_sound
                st.session_state.reminder_volume = selected_volume
                st.success(tr("notif_saved"))

            st.markdown(tr("notif_test_title"))
            test_sound_js = build_reminder_sound_script(selected_sound, selected_volume)
            components.html(f"""
            <button id="testSoundBtn" style="padding:8px 16px;border-radius:8px;border:none;
            background:#006a62;color:white;cursor:pointer;font-size:14px;">{tr("notif_test_btn")}</button>
            <script>
            {test_sound_js}
            document.getElementById('testSoundBtn').addEventListener('click', function() {{
                playReminderSound("{selected_sound}", {selected_volume});
            }});
            </script>
            """, height=60)

            st.caption(tr("notif_tip_caption"))

            st.divider()
            st.subheader(tr("notif_tts_title"))
            st.session_state.tts_enabled = st.toggle(
                tr("notif_tts_toggle"),
                value=st.session_state.tts_enabled,
            )
            st.caption(tr("notif_tts_caption"))

        # ===== NGƯỜI THÂN =====
        with sub_family:
            st.subheader(tr("family_title"))
            st.caption(tr("family_caption"))
            with st.form("invite_family_form", clear_on_submit=True):
                fcol1, fcol2 = st.columns(2)
                invite_phone = fcol1.text_input(tr("family_invite_phone"), placeholder=tr("phone_placeholder"))
                invite_name = fcol2.text_input(tr("family_invite_name"),
                                                placeholder=tr("family_invite_name_placeholder"))
                submit_invite = st.form_submit_button(tr("family_invite_btn"))
                if submit_invite:
                    invite_phone_clean = invite_phone.strip()
                    if not validate_phone(invite_phone_clean):
                        st.error(tr("family_invite_error_phone"))
                    elif invite_phone_clean == st.session_state.user_phone:
                        st.error(tr("family_invite_error_self"))
                    else:
                        ok, err = create_family_invite(
                            st.session_state.user_phone, invite_phone_clean, invite_name
                        )
                        if ok:
                            st.success(tr("family_invite_sent", phone=invite_phone_clean))
                            st.rerun()
                        else:
                            st.error(FAMILY_TABLE_MISSING_MSG if _is_missing_table_error(err)
                                      else f"{tr('family_send_error')} {err}")

            my_family_members = fetch_family_members(st.session_state.user_phone)
            if my_family_members:
                st.markdown(tr("family_list_title"))
                status_label = {"pending": tr("family_status_pending"), "accepted": tr("family_status_accepted"),
                                 "declined": tr("family_status_declined")}
                for link in my_family_members:
                    lcols = st.columns([3, 2, 2, 1])
                    lcols[0].markdown(f"**{link.get('member_name') or link.get('member_phone')}**")
                    lcols[1].markdown(link.get("member_phone", ""))
                    lcols[2].markdown(status_label.get(link.get("status"), link.get("status", "")))
                    if lcols[3].button("🗑️", key=f"del_link_{link.get('id')}"):
                        ok, err = delete_family_link(link.get("id"))
                        if ok:
                            st.rerun()
                        else:
                            st.error(FAMILY_TABLE_MISSING_MSG if _is_missing_table_error(err)
                                      else f"{tr('family_delete_error')} {err}")
            else:
                st.caption(tr("family_none"))

            st.divider()
            st.subheader(tr("family_pending_title"))
            if pending_family_invites:
                for inv in pending_family_invites:
                    icols = st.columns([3, 2, 2])
                    icols[0].markdown(f"{tr('family_owner_label')} **{inv.get('owner_phone')}**")
                    if icols[1].button(tr("family_accept_btn"), key=f"accept_{inv.get('id')}"):
                        ok, err = update_family_link_status(inv.get("id"), "accepted")
                        if ok:
                            st.success(tr("family_accept_success"))
                            st.rerun()
                        else:
                            st.error(
                                FAMILY_TABLE_MISSING_MSG if _is_missing_table_error(err) else
                                f"{tr('family_accept_error')} {err}"
                            )
                    if icols[2].button(tr("family_decline_btn"), key=f"decline_{inv.get('id')}"):
                        ok, err = update_family_link_status(inv.get("id"), "declined")
                        if ok:
                            st.rerun()
                        else:
                            st.error(FAMILY_TABLE_MISSING_MSG if _is_missing_table_error(err)
                                      else f"{tr('family_decline_error')} {err}")
            else:
                st.caption(tr("family_no_pending"))

            st.divider()
            st.subheader(tr("family_send_title"))
            owners_i_help = fetch_owners_i_help(st.session_state.user_phone)
            if not owners_i_help:
                st.caption(tr("family_send_none"))
            else:
                owner_options = {o.get("owner_phone"): o.get("owner_phone") for o in owners_i_help}

                send_mode = st.radio(
                    tr("family_send_mode"), [tr("family_send_now"), tr("family_send_scheduled")],
                    horizontal=True, key="family_reminder_send_mode",
                )
                scheduled_time = None
                if send_mode == tr("family_send_scheduled"):
                    st.caption(tr("family_send_pick_time"))
                    time_col1, time_col2 = st.columns(2)
                    selected_hour = time_col1.selectbox(
                        tr("family_send_hour"), options=list(range(1, 25)), index=7,
                        format_func=lambda h: f"{h:02d}", key="family_reminder_hour",
                    )
                    selected_minute = time_col2.selectbox(
                        tr("family_send_minute"), options=list(range(0, 60)), index=0,
                        format_func=lambda m: f"{m:02d}", key="family_reminder_minute",
                    )
                    real_hour = selected_hour % 24
                    scheduled_time = f"{real_hour:02d}:{selected_minute:02d}"

                with st.form("send_family_reminder_form", clear_on_submit=True):
                    target_owner = st.selectbox(tr("family_send_target"), options=list(owner_options.keys()))
                    reminder_msg = st.text_area(
                        tr("family_send_msg"),
                        placeholder=tr("family_send_msg_placeholder"),
                    )
                    submit_send = st.form_submit_button(tr("family_send_btn"))
                    if submit_send:
                        if not reminder_msg.strip():
                            st.warning(tr("family_send_warn_empty"))
                        else:
                            ok, err = send_family_reminder(
                                owner_phone=target_owner,
                                sender_phone=st.session_state.user_phone,
                                sender_name=st.session_state.current_profile.get("full_name", ""),
                                message=reminder_msg,
                                target_time=scheduled_time,
                            )
                            if ok:
                                st.success(tr("family_send_success"))
                            else:
                                st.error(FAMILY_TABLE_MISSING_MSG if _is_missing_table_error(err)
                                          else f"{tr('family_send_error')} {err}")

            st.caption(tr("family_footer_caption"))
