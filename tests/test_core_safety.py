import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "code")]
import safepill_core as c  # noqa: E402


def test_fake_domain_rejected():
    assert not c.is_trusted_medical_source("https://who.international-fake.com/x")

def test_real_domain_accepted():
    assert c.is_trusted_medical_source("https://www.drugs.com/aspirin.html")

def test_redirect_link_uses_title():
    assert c.is_trusted_medical_source("https://vertexaisearch.cloud.google.com/grounding-api-redirect/abc", "drugs.com")

def test_severe_pair_detected_both_orders():
    assert c.check_interaction("Aspirin", "Warfarin") is not None
    assert c.check_interaction("Warfarin", "Aspirin") is not None

def test_unknown_drug_is_not_silently_matched():
    assert c.normalize_drug_name("Thuốc lạ xyz")[0] is None

def test_brand_name_resolves():
    assert c.normalize_drug_name("Hapacol 500mg")[0] == "Paracetamol"

def test_low_confidence_when_no_evidence():
    level, banner = c.assess_answer_confidence(False, 0)
    assert level == "thấp" and banner

def test_high_confidence_needs_both_sources():
    assert c.assess_answer_confidence(True, 1)[0] == "cao"
    assert c.assess_answer_confidence(True, 0)[0] == "trung bình"

def test_cannot_save_row_missing_name_or_dose():
    blocking, _ = c.validate_pending_rows([{"keep": True, "name": "", "dose": "1 viên"}])
    assert blocking
    blocking, _ = c.validate_pending_rows([{"keep": False, "name": "", "dose": ""}])
    assert not blocking          # dòng không giữ thì không chặn

def test_dark_image_rejected():
    severe, _ = c.check_image_quality(Image.new("RGB", (1200, 900), (10, 10, 10)))
    assert severe

def test_tiny_image_rejected():
    severe, _ = c.check_image_quality(Image.new("RGB", (300, 200), (128, 128, 128)))
    assert severe

def test_coverage_note_says_no_warning_is_not_safe():
    assert "KHÔNG" in c.interaction_coverage_note([{"Tên thuốc": "Aspirin"}])
