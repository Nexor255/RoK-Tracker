import cv2
import re
import tesserocr
import numpy as np

from PIL import Image
from cv2.typing import MatLike
from typing import Tuple


def cropToRegion(image: MatLike, roi: Tuple[int, int, int, int]) -> MatLike:
    return image[int(roi[1]) : int(roi[1] + roi[3]), int(roi[0]) : int(roi[0] + roi[2])]


def cropToTextWithBorder(img: MatLike, border_size) -> MatLike:
    coords = cv2.findNonZero(cv2.bitwise_not(img))
    x, y, w, h = cv2.boundingRect(coords)

    roi = img[y : y + h, x : x + w]
    bordered = cv2.copyMakeBorder(
        roi,
        top=border_size,
        bottom=border_size,
        left=border_size,
        right=border_size,
        borderType=cv2.BORDER_CONSTANT,
        value=[255],
    )

    return bordered


def preprocessImage(
    image: MatLike,
    scale_factor: int,
    threshold: int,
    border_size: int,
    invert: bool = False,
) -> MatLike:
    if image is None or image.size == 0:
        return np.zeros((1, 1), dtype=np.uint8)
    im_big = cv2.resize(image, (0, 0), fx=scale_factor, fy=scale_factor)
    im_gray = cv2.cvtColor(im_big, cv2.COLOR_BGR2GRAY)
    if invert:
        im_gray = cv2.bitwise_not(im_gray)
    (thresh, im_bw) = cv2.threshold(im_gray, threshold, 255, cv2.THRESH_BINARY)
    im_bw = cropToTextWithBorder(im_bw, border_size)
    return im_bw


def preprocessImageRobust(
    image: MatLike,
    scale_factor: int,
    threshold: int,
    border_size: int,
    invert: bool = False,
) -> MatLike:
    """Enhanced preprocessing using HSV color masking to handle themed backgrounds.

    On themed governor profiles (e.g. Colosseum, Arena), colorful background
    pixels survive simple grayscale thresholding and create OCR noise.  This
    function converts to the HSV color space first and builds a mask that keeps
    only bright, low-saturation pixels — i.e. the white / light game-text —
    before binarising.  Falls back to the legacy path when the input is already
    single-channel.
    """
    if image is None or image.size == 0:
        return np.zeros((1, 1), dtype=np.uint8)
    im_big = cv2.resize(image, (0, 0), fx=scale_factor, fy=scale_factor)

    if len(im_big.shape) == 3 and im_big.shape[2] >= 3:
        # --- colour image: use HSV masking ---
        hsv = cv2.cvtColor(im_big, cv2.COLOR_BGR2HSV)
        v_channel = hsv[:, :, 2]
        s_channel = hsv[:, :, 1]

        # Keep bright, low-saturation pixels (white / light text)
        bright_mask = cv2.inRange(v_channel, np.array(180), np.array(255))
        low_sat_mask = cv2.inRange(s_channel, np.array(0), np.array(60))
        text_mask = cv2.bitwise_and(bright_mask, low_sat_mask)

        gray = cv2.cvtColor(im_big, cv2.COLOR_BGR2GRAY)
        masked = cv2.bitwise_and(gray, gray, mask=text_mask)

        # Invert so text becomes black-on-white (Tesseract default)
        im_bw = cv2.bitwise_not(masked)
        # Clean-up threshold
        (_, im_bw) = cv2.threshold(im_bw, threshold, 255, cv2.THRESH_BINARY)
    else:
        # --- grayscale fallback (same as preprocessImage) ---
        im_gray = im_big if len(im_big.shape) == 2 else cv2.cvtColor(im_big, cv2.COLOR_BGR2GRAY)
        if invert:
            im_gray = cv2.bitwise_not(im_gray)
        (_, im_bw) = cv2.threshold(im_gray, threshold, 255, cv2.THRESH_BINARY)

    im_bw = cropToTextWithBorder(im_bw, border_size)
    return im_bw


def ocr_number(api, image: MatLike):
    api.SetImage(Image.fromarray(image))
    score = api.GetUTF8Text()
    score = re.sub("[^0-9]", "", score)
    if not score:
        return "Unknown"
    return score


def ocr_text(api, image: MatLike):
    api.SetImage(Image.fromarray(image))
    name = api.GetUTF8Text()
    return name.rstrip("\n")


def preprocess_and_ocr_number(
    api, image: MatLike, region: Tuple[int, int, int, int], invert: bool = False
):
    cropped_image = cropToRegion(image, region)
    cropped_bw_image = preprocessImage(cropped_image, 3, 150, 12, invert)

    return ocr_number(api, cropped_bw_image)


def preprocess_and_ocr_number_robust(
    api, image: MatLike, region: Tuple[int, int, int, int], invert: bool = False
):
    """Crop, preprocess with HSV masking, and OCR a number region."""
    cropped_image = cropToRegion(image, region)
    cropped_bw_image = preprocessImageRobust(cropped_image, 3, 150, 12, invert)
    return ocr_number(api, cropped_bw_image)


def get_supported_langs(path: str) -> str:
    return str(tesserocr.get_languages(path))  # type: ignore


def pil_to_cv2(pil_image) -> MatLike:
    """Convert a PIL Image to an OpenCV numpy array (BGR format)."""
    import numpy as np

    rgb = np.array(pil_image)
    if len(rgb.shape) == 3 and rgb.shape[2] >= 3:
        return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    return rgb
