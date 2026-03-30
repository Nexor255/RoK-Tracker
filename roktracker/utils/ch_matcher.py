"""
City Hall Level Matcher — Template matching + OCR fallback.

Uses pre-captured screenshots of CH levels 1-25 to identify the level
displayed in the governor search screen via OpenCV template matching.
Falls back to Tesseract OCR if template matching confidence is too low.
"""

import cv2
import logging
import re
import numpy as np

from pathlib import Path
from typing import Dict, Tuple
from cv2.typing import MatLike
from PIL import Image
from tesserocr import PyTessBaseAPI, PSM, OEM  # type: ignore

from roktracker.utils.ocr import cropToTextWithBorder
from roktracker.utils.general import load_cv2_img

logger = logging.getLogger(__name__)

# Confidence thresholds
CONFIDENCE_HIGH = 0.90  # Early exit — no need to check further
CONFIDENCE_MIN = 0.75   # Minimum acceptable confidence

# Template matching scales for robustness against minor resolution differences
MATCH_SCALES = [1.0, 0.95, 1.05]

# Width threshold to classify single-digit vs double-digit
# Single-digit templates (1-9) are narrower than double-digit (10-25)
SINGLE_DIGIT_MAX_WIDTH = 20  # pixels in the original crop


class CHLevelMatcher:
    """City Hall level recognition via template matching + OCR fallback."""

    def __init__(self, templates_dir: Path, tesseract_path: Path):
        self.tesseract_path = tesseract_path
        self.templates: Dict[int, MatLike] = {}
        self.templates_eq: Dict[int, MatLike] = {}  # histogram-equalized
        self.single_digit_levels: list[int] = []
        self.double_digit_levels: list[int] = []

        self._load_templates(templates_dir)

    def _load_templates(self, templates_dir: Path) -> None:
        """Load all 25 templates, convert to grayscale, classify by digit count."""
        for level in range(1, 26):
            path = templates_dir / f"{level}.png"
            if not path.exists():
                logger.warning(f"Missing CH template: {path}")
                continue

            img = load_cv2_img(path, cv2.IMREAD_UNCHANGED)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
            self.templates[level] = gray

            # Histogram-equalized variant for lighting normalization
            self.templates_eq[level] = cv2.equalizeHist(gray)

            # Classify by width
            if gray.shape[1] <= SINGLE_DIGIT_MAX_WIDTH:
                self.single_digit_levels.append(level)
            else:
                self.double_digit_levels.append(level)

        logger.info(
            f"Loaded {len(self.templates)} CH templates "
            f"(single-digit: {self.single_digit_levels}, "
            f"double-digit: {self.double_digit_levels})"
        )

    def _match_against_group(
        self,
        crop_gray: MatLike,
        crop_eq: MatLike,
        levels: list[int],
    ) -> Tuple[int, float]:
        """Run template matching against a specific group of levels.

        Uses dual-method voting: TM_CCOEFF_NORMED + TM_CCORR_NORMED.
        Both methods must agree on the same level for the result to be accepted.
        Tries multiple scales for robustness.

        Returns (best_level, best_confidence) or (0, 0.0) on failure.
        """
        best_level = 0
        best_confidence = 0.0

        for level in levels:
            template = self.templates[level]
            template_eq = self.templates_eq[level]

            for scale in MATCH_SCALES:
                # Scale the template
                if scale != 1.0:
                    h, w = template.shape[:2]
                    new_w = max(1, int(w * scale))
                    new_h = max(1, int(h * scale))
                    tmpl = cv2.resize(template, (new_w, new_h))
                    tmpl_eq = cv2.resize(template_eq, (new_w, new_h))
                else:
                    tmpl = template
                    tmpl_eq = template_eq

                # Skip if template is larger than crop
                if (
                    tmpl.shape[0] > crop_gray.shape[0]
                    or tmpl.shape[1] > crop_gray.shape[1]
                ):
                    continue

                # Method 1: TM_CCOEFF_NORMED (on raw grayscale)
                result_ccoeff = cv2.matchTemplate(
                    crop_gray, tmpl, cv2.TM_CCOEFF_NORMED
                )
                _, max_val_ccoeff, _, _ = cv2.minMaxLoc(result_ccoeff)

                # Method 2: TM_CCORR_NORMED (on histogram-equalized)
                result_ccorr = cv2.matchTemplate(
                    crop_eq, tmpl_eq, cv2.TM_CCORR_NORMED
                )
                _, max_val_ccorr, _, _ = cv2.minMaxLoc(result_ccorr)

                # Take the minimum of both methods (conservative — both must agree)
                confidence = min(max_val_ccoeff, max_val_ccorr)

                if confidence > best_confidence:
                    best_confidence = confidence
                    best_level = level

                # Early exit on very high confidence
                if best_confidence >= CONFIDENCE_HIGH:
                    return best_level, best_confidence

        return best_level, best_confidence

    def match(self, crop: MatLike) -> Tuple[int, float]:
        """Primary: two-phase template matching.

        Phase 1: Classify crop width → single or double digit group
        Phase 2: Match against that group, then try the other group if needed

        Returns (level, confidence) or (0, 0.0) on failure.
        """
        # Convert to grayscale
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if len(crop.shape) == 3 else crop
        eq = cv2.equalizeHist(gray)

        # Phase 1: Determine likely digit count from crop width
        crop_w = gray.shape[1]

        if crop_w <= SINGLE_DIGIT_MAX_WIDTH:
            primary_group = self.single_digit_levels
            secondary_group = self.double_digit_levels
        else:
            primary_group = self.double_digit_levels
            secondary_group = self.single_digit_levels

        # Phase 2a: Match against primary group
        level, confidence = self._match_against_group(gray, eq, primary_group)
        if confidence >= CONFIDENCE_MIN:
            return level, confidence

        # Phase 2b: Try secondary group as fallback
        level2, confidence2 = self._match_against_group(gray, eq, secondary_group)
        if confidence2 > confidence:
            level, confidence = level2, confidence2

        if confidence >= CONFIDENCE_MIN:
            return level, confidence

        return 0, 0.0

    def ocr_fallback(self, crop: MatLike) -> int:
        """Fallback: Tesseract OCR with aggressive preprocessing.

        Returns CH level (1-25) or 0 on failure.
        """
        try:
            # Preprocess: upscale, adaptive threshold, morphological close
            preprocessed = self._preprocess_for_ocr(crop)

            with PyTessBaseAPI(
                path=str(self.tesseract_path), psm=PSM.SINGLE_WORD, oem=OEM.LSTM_ONLY
            ) as api:
                api.SetVariable("tessedit_char_whitelist", "0123456789")

                # Try SINGLE_WORD first (best for 2-digit numbers)
                api.SetImage(Image.fromarray(preprocessed))
                text = api.GetUTF8Text().strip()
                text = re.sub("[^0-9]", "", text)

                if text:
                    val = int(text)
                    if 1 <= val <= 25:
                        return val

                # Try SINGLE_CHAR (better for single-digit like "1")
                api.SetPageSegMode(PSM.SINGLE_CHAR)
                api.SetImage(Image.fromarray(preprocessed))
                text = api.GetUTF8Text().strip()
                text = re.sub("[^0-9]", "", text)

                if text:
                    val = int(text)
                    if 1 <= val <= 25:
                        return val

        except Exception as e:
            logger.warning(f"OCR fallback failed: {e}")

        return 0

    def _preprocess_for_ocr(self, crop: MatLike) -> MatLike:
        """Aggressive preprocessing for the tiny CH level field."""
        # Upscale 6× for better Tesseract accuracy
        big = cv2.resize(crop, (0, 0), fx=6, fy=6, interpolation=cv2.INTER_CUBIC)

        # Convert to grayscale
        if len(big.shape) == 3:
            gray = cv2.cvtColor(big, cv2.COLOR_BGR2GRAY)
        else:
            gray = big

        # Adaptive thresholding — handles gradient/textured backgrounds
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 8
        )

        # Morphological close — reconnects broken strokes from bold italic font
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

        # Invert if needed (ensure dark text on white background)
        # Check if the image is mostly dark (text region) or mostly light
        if np.mean(closed) < 128:
            closed = cv2.bitwise_not(closed)

        # Crop to text bounding box with border
        try:
            result = cropToTextWithBorder(closed, 10)
        except Exception:
            result = closed

        return result

    def identify(self, crop: MatLike) -> int:
        """Full pipeline: template match → OCR fallback.

        Returns the CH level (1-25) or 0 if all methods fail.
        """
        # Primary: template matching
        level, confidence = self.match(crop)
        if level > 0:
            logger.debug(f"CH template match: level={level}, confidence={confidence:.3f}")
            return level

        # Fallback: OCR
        level = self.ocr_fallback(crop)
        if level > 0:
            logger.debug(f"CH OCR fallback: level={level}")
            return level

        logger.debug("CH identification failed — all methods exhausted")
        return 0
