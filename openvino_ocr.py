"""
SafePill - Offline OCR fallback using Intel OpenVINO
Pipeline: horizontal-text-detection-0001 (find text regions)
       -> text-recognition-0014 (read text in each region, CTC decode)

Usage:
    python openvino_ocr.py path/to/prescription_image.jpg
"""

import sys
import cv2
import numpy as np
from openvino.runtime import Core

# ---- Config: alphabet used by text-recognition-0014 ----
# '#' at index 0 is the CTC "blank" symbol, not a real character
ALPHABET = "#0123456789abcdefghijklmnopqrstuvwxyz"

DET_MODEL_PATH = "models/horizontal-text-detection-0001.xml"
REC_MODEL_PATH = "models/text-recognition-0014.xml"


def load_models():
    core = Core()
    det_model = core.compile_model(core.read_model(DET_MODEL_PATH), "CPU")
    rec_model = core.compile_model(core.read_model(REC_MODEL_PATH), "CPU")
    return det_model, rec_model


def detect_text_boxes(det_model, image_bgr, conf_threshold=0.3):
    """Run horizontal-text-detection-0001. Returns list of (x_min, y_min, x_max, y_max)."""
    input_layer = det_model.input(0)
    output_layer = det_model.output("boxes")

    n, c, h, w = input_layer.shape  # expects 1,3,704,704
    resized = cv2.resize(image_bgr, (w, h))
    blob = resized.transpose(2, 0, 1)[np.newaxis, ...].astype(np.float32)

    result = det_model([blob])[output_layer]  # shape (100, 5)

    orig_h, orig_w = image_bgr.shape[:2]
    scale_x, scale_y = orig_w / w, orig_h / h

    boxes = []
    for x_min, y_min, x_max, y_max, conf in result:
        if conf < conf_threshold:
            continue
        boxes.append((
            int(x_min * scale_x), int(y_min * scale_y),
            int(x_max * scale_x), int(y_max * scale_y),
        ))
    return boxes


def recognize_text(rec_model, image_bgr, box):
    """Run text-recognition-0014 on a single cropped box. Returns decoded string."""
    input_layer = rec_model.input(0)
    output_layer = rec_model.output("logits")

    n, c, h, w = input_layer.shape  # expects 1,1,32,128

    x_min, y_min, x_max, y_max = box
    crop = image_bgr[max(0, y_min):y_max, max(0, x_min):x_max]
    if crop.size == 0:
        return ""

    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, (w, h))
    blob = resized[np.newaxis, np.newaxis, ...].astype(np.float32)

    result = rec_model([blob])[output_layer]  # shape (16, 1, 37) -> W, B, L

    # CTC greedy decode: argmax per timestep, collapse repeats, drop blanks
    seq = np.argmax(result[:, 0, :], axis=1)  # length 16
    decoded = []
    prev = -1
    for idx in seq:
        if idx != prev and idx != 0:  # 0 = blank
            decoded.append(ALPHABET[idx])
        prev = idx
    return "".join(decoded)


def main():
    if len(sys.argv) < 2:
        print("Usage: python openvino_ocr.py <image_path>")
        sys.exit(1)

    image_path = sys.argv[1]
    image = cv2.imread(image_path)
    if image is None:
        print(f"Could not read image: {image_path}")
        sys.exit(1)

    print("Loading OpenVINO models...")
    det_model, rec_model = load_models()

    print("Detecting text regions...")
    boxes = detect_text_boxes(det_model, image)
    print(f"Found {len(boxes)} text region(s)")

    results = []
    for box in boxes:
        text = recognize_text(rec_model, image, box)
        if text:
            results.append((box, text))
            print(f"  {box} -> '{text}'")

    full_text = " ".join(t for _, t in results)
    print("\n--- Combined OCR result ---")
    print(full_text if full_text else "(no text recognized)")

    return full_text


if __name__ == "__main__":
    main()


