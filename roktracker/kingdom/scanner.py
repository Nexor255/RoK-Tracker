import datetime
import logging
import re
from roktracker.kingdom.pandas_handler import PandasHandler
from roktracker.utils.output_formats import OutputFormats
import roktracker.utils.rok_ui_positions as rok_ui
import shutil
import time
import ctypes
from ctypes import wintypes
import numpy as np

from dummy_root import get_app_root
from pathlib import Path
from roktracker.utils.adb import *
from roktracker.utils.general import *
from roktracker.utils.ocr import *
from roktracker.utils.ch_matcher import CHLevelMatcher
from roktracker.kingdom.types.additional_data import AdditionalData
from roktracker.kingdom.types.governor_data import GovernorData
from tesserocr import PyTessBaseAPI, PSM, OEM  # type: ignore (tesserocr has no type defs)
from typing import Callable, List
from PIL import Image

from roktracker.utils.types.full_config import FormatsConfig, FullConfig
from roktracker.utils.types.scan_preset import ScanItems, ScanOptions, ScanPreset

logger = logging.getLogger(__name__)

def get_clipboard_text_ctypes() -> str:
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    
    user32.OpenClipboard.argtypes = [wintypes.HWND]
    user32.OpenClipboard.restype = wintypes.BOOL
    
    user32.GetClipboardData.argtypes = [wintypes.UINT]
    user32.GetClipboardData.restype = wintypes.HANDLE
    
    user32.CloseClipboard.argtypes = []
    user32.CloseClipboard.restype = wintypes.BOOL
    
    kernel32.GlobalLock.argtypes = [wintypes.HANDLE]
    kernel32.GlobalLock.restype = wintypes.c_void_p
    
    kernel32.GlobalUnlock.argtypes = [wintypes.HANDLE]
    kernel32.GlobalUnlock.restype = wintypes.BOOL
    
    kernel32.GlobalSize.argtypes = [wintypes.HANDLE]
    kernel32.GlobalSize.restype = ctypes.c_size_t
    
    CF_UNICODETEXT = 13
    
    if not user32.OpenClipboard(None):
        raise RuntimeError("Failed to open clipboard")
    
    try:
        handle = user32.GetClipboardData(CF_UNICODETEXT)
        if not handle:
            raise RuntimeError("No clipboard data")
        
        ptr = kernel32.GlobalLock(handle)
        if not ptr:
            raise RuntimeError("Failed to lock clipboard data")
        
        try:
            size = kernel32.GlobalSize(handle)
            if size > 0:
                raw_bytes = ctypes.string_at(ptr, size)
                val = raw_bytes.decode('utf-16-le', errors='ignore')
            else:
                val = ctypes.c_wchar_p(ptr).value
                
            if not val:
                raise RuntimeError("Clipboard is empty")
            return val
        finally:
            kernel32.GlobalUnlock(handle)
    finally:
        user32.CloseClipboard()

def empty_clipboard():
    user32 = ctypes.windll.user32
    if not user32.OpenClipboard(None):
        return
    try:
        user32.EmptyClipboard()
    finally:
        user32.CloseClipboard()

def parse_clipboard_parcel(raw: str) -> str:
    """Extract clipboard text from Android 'service call clipboard' parcel output.

    The parcel contains multiple UTF-16LE strings (MIME types like 'text/plain',
    labels, and the actual clipboard text).  We decode ALL strings from the hex
    data and return the **last** one that isn't a MIME-type or metadata string,
    since the actual clipboard text is always the final string in the parcel.
    """
    if not raw or "Parcel" not in raw:
        return ""

    # Extract all 8-char hex words from the parcel dump
    hex_words = re.findall(r"\b([0-9a-fA-F]{8})\b", raw)
    if len(hex_words) < 5:
        return ""

    # Convert hex display to memory-order bytes (LE: reverse each 4-byte word)
    all_bytes = b""
    for w in hex_words:
        b = bytes.fromhex(w)
        all_bytes += bytes([b[3], b[2], b[1], b[0]])

    # Scan for all embedded UTF-16LE strings (length-prefixed int32 + data)
    strings_found = []
    offset = 0
    while offset <= len(all_bytes) - 4:
        str_len = int.from_bytes(all_bytes[offset : offset + 4], "little")
        if 1 <= str_len <= 500:
            data_start = offset + 4
            data_end = data_start + str_len * 2
            if data_end <= len(all_bytes):
                try:
                    text = all_bytes[data_start:data_end].decode("utf-16-le")
                    printable = sum(1 for c in text if c.isprintable())
                    if printable >= max(1, len(text) // 2):
                        strings_found.append(text)
                        # Advance past this string (align to 4-byte boundary)
                        aligned_end = data_end + (4 - data_end % 4) % 4
                        offset = max(offset + 4, aligned_end)
                        continue
                except Exception:
                    pass
        offset += 4

    if not strings_found:
        return ""

    # Filter out MIME types and known metadata, return the last real string
    skip_prefixes = ("text/", "application/", "android.", "com.android")
    for text in reversed(strings_found):
        stripped = text.strip()
        if not stripped:
            continue
        lower = stripped.lower()
        if any(lower.startswith(p) for p in skip_prefixes):
            continue
        # Skip strings that look like MIME types (e.g. "image/png")
        if "/" in lower and len(lower) < 40 and " " not in lower:
            continue
        return stripped

    # All strings were metadata — return the last one as a last resort
    return strings_found[-1].strip()


def clean_clipboard_name(raw_name: str) -> str:
    """Strip Android ClipData metadata that some emulators sync to the host clipboard.

    BlueStacks (and similar emulators) sometimes sync the raw ClipData parcel
    to the Windows clipboard instead of just the plain-text payload.  This
    produces names like:
        mass_copytext/plainA?Lc99H1
        mass_copytext/plain\x00\x00ActualName

    The real governor name starts after the MIME-type and a few junk bytes.
    """
    if not raw_name:
        return ""

    # Pattern: "mass_copy" + "text/plain" + 1-4 junk chars + real name
    # Also handle with or without null bytes
    pattern = re.compile(
        r"^.*?text/plain.{0,6}?(?=[A-Za-z0-9\u0600-\u06FF\u0400-\u04FF"
        r"\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af])",
        re.DOTALL,
    )
    cleaned = pattern.sub("", raw_name)

    # If regex didn't strip anything useful, try simpler approach
    if cleaned == raw_name and "text/plain" in raw_name:
        # Find "text/plain" and take everything after it + a few junk bytes
        idx = raw_name.index("text/plain") + len("text/plain")
        remainder = raw_name[idx:]
        # Skip leading non-alphanumeric junk (null bytes, control chars)
        remainder = remainder.lstrip("\x00\x01\x02\x03\x04\x05\x06\x07"
                                      "\x08\t\n\x0b\x0c\r\x0e\x0f?")
        if remainder:
            cleaned = remainder

    # Final cleanup: remove null bytes and control characters
    cleaned = re.sub(r"[\x00-\x08\x0e-\x1f]", "", cleaned)

    return cleaned.strip() if cleaned.strip() else raw_name.strip()


def default_gov_callback(gov: GovernorData, extra: AdditionalData) -> None:
    pass


def default_state_callback(msg: str) -> None:
    pass


def default_ask_continue(msg: str) -> bool:
    return False


def default_output_handler(msg: str) -> None:
    console.log(msg)
    pass


def scan_preset_to_scan_options(preset: ScanPreset) -> ScanOptions:
    return ScanOptions(
        id=ScanItems.ID in preset.selections,
        name=ScanItems.NAME in preset.selections,
        power=ScanItems.POWER in preset.selections,
        killpoints=ScanItems.KILLPOINTS in preset.selections,
        alliance=ScanItems.ALLIANCE in preset.selections,
        t1_kills=ScanItems.T1_KILLS in preset.selections,
        t2_kills=ScanItems.T2_KILLS in preset.selections,
        t3_kills=ScanItems.T3_KILLS in preset.selections,
        t4_kills=ScanItems.T4_KILLS in preset.selections,
        t5_kills=ScanItems.T5_KILLS in preset.selections,
        ranged=ScanItems.RANGED in preset.selections,
        deaths=ScanItems.DEATHS in preset.selections,
        assistance=ScanItems.ASSISTANCE in preset.selections,
        gathered=ScanItems.GATHERED in preset.selections,
        helps=ScanItems.HELPS in preset.selections,
    )


class KingdomScanner:
    def __init__(self, config, scan_options, port):
        self.run_id = generate_random_id(8)
        self.scan_times = []
        self.start_date = datetime.date.today()
        self.stop_scan = False
        self.scan_start_time = time.time()

        self.config = config
        self.timings = config.scan.timings.model_dump()
        self.max_random_delay = config.scan.timings.max_random

        self.advanced_scroll = config.scan.advanced_scroll
        self.scan_options = scan_options
        self.abort = False
        self.inactive_players = 0

        # TODO: Load paths from config
        self.root_dir = get_app_root()
        self.tesseract_path = Path(self.root_dir / "deps" / "tessdata")
        self.img_path = Path(self.root_dir / "temp_images")
        self.img_path.mkdir(parents=True, exist_ok=True)
        self.scan_path = Path(self.root_dir / "scans_kingdom")
        self.scan_path.mkdir(parents=True, exist_ok=True)
        self.inactive_path = Path(
            self.root_dir / "inactives" / str(self.start_date) / str(self.run_id)
        )
        self.review_path = Path(
            self.root_dir / "manual_review" / str(self.start_date) / str(self.run_id)
        )
        self.created_review_path = False

        self.gov_callback = default_gov_callback
        self.state_callback = default_state_callback
        self.ask_continue = default_ask_continue
        self.output_handler = default_output_handler

        # City Hall verification state
        self._in_search_screen = False
        self._ch_matcher = CHLevelMatcher(
            self.root_dir / "deps" / "ch_templates" / "city_hall_numbers",
            self.tesseract_path,
        )

        self.adb_client = AdvancedAdbClient(
            str(self.root_dir / "deps" / "platform-tools" / "adb.exe"),
            port,
            config.general.emulator,
            self.root_dir / "deps" / "inputs",
        )

        # Persistent Tesseract API instance (avoid expensive re-init per governor)
        self._tess_api = PyTessBaseAPI(
            path=str(self.tesseract_path), psm=PSM.SINGLE_WORD, oem=OEM.LSTM_ONLY
        )


    def set_governor_callback(
        self, cb: Callable[[GovernorData, AdditionalData], None]
    ) -> None:
        self.gov_callback = cb

    def set_state_callback(self, cb: Callable[[str], None]):
        self.state_callback = cb

    def set_continue_handler(self, cb: Callable[[str], bool]):
        self.ask_continue = cb

    def set_output_handler(self, cb: Callable[[str], None]):
        self.output_handler = cb

    def _get_android_api_level(self) -> int:
        """Get the Android API level of the connected emulator (cached)."""
        if hasattr(self, '_android_api_level'):
            return self._android_api_level
        try:
            result = self.adb_client.secure_adb_shell(
                "getprop ro.build.version.sdk"
            )
            level = int(result.strip())
            self._android_api_level = level
            logger.info(f"Detected Android API level: {level}")
            return level
        except Exception as e:
            logger.debug(f"Failed to detect Android API level: {e}")
            self._android_api_level = 0
            return 0

    def _read_clipboard_via_adb(self) -> str:
        """Read clipboard text directly from the Android emulator via ADB.

        The clipboard service method number for getPrimaryClip depends on
        the Android version:
          - Android 5-8  (API 21-27): method 2 = getPrimaryClip
          - Android 9+   (API 28+) : method 3 = getPrimaryClip
                                      method 2 = clearPrimaryClip (destructive!)
        We detect the API level once and use the correct method.
        """
        api_level = self._get_android_api_level()

        if api_level >= 28:
            # Android 9+: getPrimaryClip is method 3.
            # Method 2 is clearPrimaryClip — must NOT be called.
            methods = [3]
        elif api_level > 0:
            # Android 5-8: getPrimaryClip is method 2.
            methods = [2]
        else:
            # Unknown version: try 3 first (safe read-only on all versions),
            # then 2 as fallback.
            methods = [3, 2]

        for method_num in methods:
            try:
                raw = self.adb_client.secure_adb_shell(
                    f"service call clipboard {method_num} s16 com.android.shell"
                )
                parsed = parse_clipboard_parcel(raw)
                if parsed:
                    logger.info(
                        f"ADB clipboard (method {method_num}) parsed name: {parsed!r}"
                    )
                    return parsed
            except Exception as e:
                logger.debug(f"ADB clipboard method {method_num} failed: {e}")

        logger.info("ADB clipboard parse returned empty")
        return ""

    def _copy_governor_name(self, tap_positions: dict) -> str:
        """Copy governor name via tap and read from clipboard.

        Retries the full tap → read cycle up to 3 times.
        For each attempt:
          1. Tap the name-copy button in the game
          2. Try reading the Android clipboard via ADB (most reliable)
          3. Fall back to reading the Windows clipboard
        """
        for attempt in range(3):
            # Clear Windows clipboard before copying so we can detect when the new value arrives
            empty_clipboard()
            
            # Tap the name-copy button
            self.adb_client.secure_adb_tap(tap_positions["name_copy"])
            wait_random_range(
                self.timings["copy_wait"], self.max_random_delay
            )

            # --- Strategy 1: read directly from Android via ADB ---
            name = self._read_clipboard_via_adb()
            if name:
                return name

            # --- Strategy 2: poll the Windows clipboard (emulator sync) ---
            for _ in range(15):  # ~1.5 s
                try:
                    name = get_clipboard_text_ctypes()
                    if name:
                        cleaned = clean_clipboard_name(name)
                        if cleaned:
                            return cleaned
                except Exception:
                    pass
                time.sleep(0.1)

            logger.info(f"Name copy attempt {attempt + 1}/3 failed, retrying")

        # All attempts exhausted
        logger.warning("Name copy failed after 3 attempts")
        return ""

    def get_remaining_time(self, remaining_govs: int) -> float:
        return (sum(self.scan_times, start=0) / len(self.scan_times)) * remaining_govs

    def save_failed(
        self, fail_type: str, gov_data: GovernorData, reconstructed: bool = False
    ):
        pre = "Unset"
        if fail_type == "kills":
            if reconstructed:
                pre = "R"
                logging.log(
                    logging.INFO,
                    f"""Kills for {gov_data.name} ({to_int_check(gov_data.id)}) reconstructed, t1 might be off by up to 4 kills.""",
                )
            else:
                pre = "F"
                logging.log(
                    logging.WARNING,
                    f"""Kills for {gov_data.name} ({to_int_check(gov_data.id)}) don't check out, manually need to look at them!""",
                )
        elif fail_type == "power":
            pre = "P"
            logging.log(
                logging.WARNING,
                f"""Power for {gov_data.name} ({to_int_check(gov_data.id)}) is higher then previous governor, manually need to look at it!""",
            )

        if not self.created_review_path:
            self.review_path.mkdir(parents=True, exist_ok=True)
            self.created_review_path = True

        shutil.copy(
            Path(self.img_path / "gov_info.png"),
            Path(self.review_path / f"""{pre}{gov_data.id}-profile.png"""),
        )
        if fail_type == "kills":
            shutil.copy(
                Path(self.img_path / "kills_tier.png"),
                Path(self.review_path / f"""{pre}{gov_data.id}-kills.png"""),
            )

    def get_gov_position(self, current_position, skips):
        # Positions for next governor to check
        Y = [285, 390, 490, 590, 605, 705, 805]

        # skips only are relevant in the first 4 governors
        if current_position + skips < 4:
            return Y[current_position + skips]
        else:
            if current_position < 998:
                return Y[4]
            elif current_position == 998:
                return Y[5]
            elif current_position == 999:
                return Y[6]
            else:
                console.log("Reached final governor on the screen. Scan complete.")
                logging.log(
                    logging.INFO, "Reached final governor on the screen. Scan complete."
                )
                return Y[6]

    def is_page_needed(self, page: int) -> bool:
        match page:
            case 1:
                return (
                    self.scan_options.id
                    or self.scan_options.name
                    or self.scan_options.power
                    or self.scan_options.killpoints
                    or self.scan_options.alliance
                )
            case 2:
                return (
                    self.scan_options.t1_kills
                    or self.scan_options.t2_kills
                    or self.scan_options.t3_kills
                    or self.scan_options.t4_kills
                    or self.scan_options.t5_kills
                    or self.scan_options.ranged
                )
            case 3:
                return (
                    self.scan_options.deaths
                    or self.scan_options.assistance
                    or self.scan_options.gathered
                    or self.scan_options.helps
                )
            case _:
                return False

    def scan_governor(
        self,
        current_player: int,
        track_inactives: bool,
    ) -> GovernorData:
        start_time = time.time()
        governor_data = GovernorData()

        self.state_callback("Opening governor")
        # Open governor
        self.adb_client.secure_adb_shell(
            f"input tap 690 "
            + str(self.get_gov_position(current_player, self.inactive_players))
        )

        wait_random_range(self.timings["gov_open"], self.max_random_delay)

        gov_info = False
        count = 0
        ui_positions = {}
        tap_positions = {}

        while not (gov_info):
            screenshot_pil = self.adb_client.secure_adb_screencap()
            image_check = pil_to_cv2(screenshot_pil)
            image_check_gray = cv2.cvtColor(image_check, cv2.COLOR_BGR2GRAY)

            # Checking for more info — use HSV masking to handle themed profiles
            im_check_more_info = cropToRegion(
                image_check, rok_ui.ocr_regions["more_info"]
            )
            im_check_more_info_bw = preprocessImageRobust(im_check_more_info, 3, 150, 10, True)
            check_more_info = ""

            self._tess_api.SetPageSegMode(PSM.AUTO)
            self._tess_api.SetVariable("tessedit_char_whitelist", "MoreInfo")
            self._tess_api.SetImage(Image.fromarray(im_check_more_info_bw))  # type: ignore
            check_more_info = self._tess_api.GetUTF8Text()
            self._tess_api.SetVariable("tessedit_char_whitelist", "")

            # Probably tapped governor is inactive and needs to be skipped
            if not more_info_present(check_more_info):
                self.inactive_players += 1
                if track_inactives:
                    roiInactive = (
                        0,
                        self.get_gov_position(current_player, self.inactive_players - 1)
                        - 100,
                        1400,
                        200,
                    )
                    image_inactive_raw = cropToRegion(image_check, roiInactive)
                    write_cv2_img(
                        image_inactive_raw,
                        self.inactive_path / f"inactive {self.inactive_players:03}.png",
                        "png",
                    )

                if self.advanced_scroll:
                    self.adb_client.adb_send_events(
                        "Touch",
                        "kingdom_1_person_scroll.txt",
                    )
                else:
                    self.adb_client.secure_adb_shell(f"input swipe 690 605 690 540")
                self.adb_client.secure_adb_shell(
                    f"input tap 690 "
                    + str(self.get_gov_position(current_player, self.inactive_players)),
                )
                count += 1
                wait_random_range(self.timings["gov_open"], self.max_random_delay)
                if count == 10:
                    cont = self.ask_continue("Could not find user, retry?")
                    if cont:
                        count = 0
                    else:
                        break
            else:
                gov_info = True

                # Check profile version (reuse in-memory image)
                # Try original grayscale first (works on normal profiles),
                # then fallback to robust HSV preprocessing (themed profiles).
                im_check_profile = cropToRegion(
                    image_check_gray, rok_ui.ocr_check_profile_version
                )
                check_profile_version = ""

                self._tess_api.SetPageSegMode(PSM.AUTO)
                self._tess_api.SetVariable("tessedit_char_whitelist", "Aclaim")
                self._tess_api.SetImage(Image.fromarray(im_check_profile))  # type: ignore
                check_profile_version = self._tess_api.GetUTF8Text()
                self._tess_api.SetVariable("tessedit_char_whitelist", "")

                # Fallback: robust preprocessing for themed profiles
                if "Acclaim" not in check_profile_version:
                    im_check_profile_color = cropToRegion(
                        image_check, rok_ui.ocr_check_profile_version
                    )
                    im_check_profile_bw = preprocessImageRobust(im_check_profile_color, 3, 150, 10, True)
                    self._tess_api.SetPageSegMode(PSM.AUTO)
                    self._tess_api.SetVariable("tessedit_char_whitelist", "Aclaim")
                    self._tess_api.SetImage(Image.fromarray(im_check_profile_bw))  # type: ignore
                    check_profile_version = self._tess_api.GetUTF8Text()
                    self._tess_api.SetVariable("tessedit_char_whitelist", "")

                if "Acclaim" in check_profile_version:
                    ui_positions = rok_ui.ocr_regions
                    tap_positions = rok_ui.tap_positions
                else:
                    ui_positions = rok_ui.ocr_regions_old
                    tap_positions = rok_ui.tap_positions_old

                break

        if self.is_page_needed(1):
            self.state_callback("Scanning general page")

            # take screenshot before copying the name
            gov_info_pil = self.adb_client.secure_adb_screencap()
            gov_info_pil.save(self.img_path / "gov_info.png")  # keep for review
            image = pil_to_cv2(gov_info_pil)

            if self.scan_options.name:
                # nickname copy — uses ADB clipboard read + Windows fallback
                copied_name = self._copy_governor_name(tap_positions)
                if copied_name:
                    governor_data.name = copied_name
                else:
                    console.log("Name copy failed after all attempts")
                    logging.log(
                        logging.WARNING,
                        "Name copy failed after all attempts",
                    )

            # 1st image data (ID, Power, Killpoints, Alliance)
            api = self._tess_api
            api.SetPageSegMode(PSM.SINGLE_WORD)
            if self.scan_options.power:
                im_gov_power = cropToRegion(image, ui_positions["power"])
                im_gov_power_bw = preprocessImage(im_gov_power, 3, 100, 12, True)
                governor_data.power = ocr_number(api, im_gov_power_bw)
                # Fallback to robust preprocessing for themed profiles
                if governor_data.power == "Unknown":
                    im_gov_power_bw = preprocessImageRobust(im_gov_power, 3, 100, 12, True)
                    governor_data.power = ocr_number(api, im_gov_power_bw)

            if self.scan_options.killpoints:
                im_gov_killpoints = cropToRegion(
                    image, ui_positions["killpoints"]
                )
                im_gov_killpoints_bw = preprocessImage(
                    im_gov_killpoints, 3, 100, 12, True
                )
                governor_data.killpoints = ocr_number(api, im_gov_killpoints_bw)
                # Fallback to robust preprocessing for themed profiles
                if governor_data.killpoints == "Unknown":
                    im_gov_killpoints_bw = preprocessImageRobust(
                        im_gov_killpoints, 3, 100, 12, True
                    )
                    governor_data.killpoints = ocr_number(api, im_gov_killpoints_bw)

            api.SetPageSegMode(PSM.SINGLE_LINE)
            if self.scan_options.id:
                im_gov_id = cropToRegion(image, ui_positions["gov_id"])
                im_gov_id_gray = cv2.cvtColor(im_gov_id, cv2.COLOR_BGR2GRAY)
                im_gov_id_gray = cv2.bitwise_not(im_gov_id_gray)
                (thresh, im_gov_id_bw) = cv2.threshold(
                    im_gov_id_gray, 120, 255, cv2.THRESH_BINARY
                )
                governor_data.id = ocr_number(api, im_gov_id_bw)
                # Fallback to robust preprocessing for themed profiles
                if governor_data.id == "Unknown":
                    im_gov_id_bw = preprocessImageRobust(im_gov_id, 3, 120, 12, True)
                    governor_data.id = ocr_number(api, im_gov_id_bw)

            if self.scan_options.alliance:
                im_alliance_tag = cropToRegion(
                    image, ui_positions["alliance_name"]
                )
                im_alliance_bw = preprocessImage(im_alliance_tag, 3, 50, 12, True)

                governor_data.alliance = ocr_text(api, im_alliance_bw)

        if self.is_page_needed(2):
            # kills tier
            self.adb_client.secure_adb_tap(tap_positions["open_kills"])
            self.state_callback("Scanning kills page")
            wait_random_range(self.timings["kills_open"], self.max_random_delay)

            kills_pil = self.adb_client.secure_adb_screencap()
            kills_pil.save(self.img_path / "kills_tier.png")  # keep for review
            image2 = pil_to_cv2(kills_pil)

            api = self._tess_api
            api.SetPageSegMode(PSM.SINGLE_WORD)
            if self.scan_options.t1_kills:
                # tier 1 Kills
                governor_data.t1_kills = preprocess_and_ocr_number(
                    api, image2, ui_positions["t1_kills"]
                )

                # tier 1 KP
                governor_data.t1_kp = preprocess_and_ocr_number(
                    api, image2, ui_positions["t1_killpoints"]
                )

            if self.scan_options.t2_kills:
                # tier 2 Kills
                governor_data.t2_kills = preprocess_and_ocr_number(
                    api, image2, ui_positions["t2_kills"]
                )

                # tier 2 KP
                governor_data.t2_kp = preprocess_and_ocr_number(
                    api, image2, ui_positions["t2_killpoints"]
                )

            if self.scan_options.t3_kills:
                # tier 3 Kills
                governor_data.t3_kills = preprocess_and_ocr_number(
                    api, image2, ui_positions["t3_kills"]
                )

                # tier 3 KP
                governor_data.t3_kp = preprocess_and_ocr_number(
                    api, image2, ui_positions["t3_killpoints"]
                )

            if self.scan_options.t4_kills:
                # tier 4 Kills
                governor_data.t4_kills = preprocess_and_ocr_number(
                    api, image2, ui_positions["t4_kills"]
                )

                # tier 4 KP
                governor_data.t4_kp = preprocess_and_ocr_number(
                    api, image2, ui_positions["t4_killpoints"]
                )

            if self.scan_options.t5_kills:
                # tier 5 Kills
                governor_data.t5_kills = preprocess_and_ocr_number(
                    api, image2, ui_positions["t5_kills"]
                )

                # tier 5 KP
                governor_data.t5_kp = preprocess_and_ocr_number(
                    api, image2, ui_positions["t5_killpoints"]
                )

            if self.scan_options.ranged:
                # ranged points
                governor_data.ranged_points = preprocess_and_ocr_number(
                    api, image2, ui_positions["ranged_points"]
                )

        if self.is_page_needed(3):
            # More info tab
            self.adb_client.secure_adb_tap(tap_positions["more_info"])
            self.state_callback("Scanning more info page")
            wait_random_range(self.timings["info_open"], self.max_random_delay)
            image3 = pil_to_cv2(self.adb_client.secure_adb_screencap())

            api = self._tess_api
            api.SetPageSegMode(PSM.SINGLE_WORD)
            if self.scan_options.deaths:
                governor_data.dead = preprocess_and_ocr_number(
                    api, image3, ui_positions["deads"], True
                )

            if self.scan_options.assistance:
                governor_data.rss_assistance = preprocess_and_ocr_number(
                    api, image3, ui_positions["rss_assisted"], True
                )

            if self.scan_options.gathered:
                governor_data.rss_gathered = preprocess_and_ocr_number(
                    api, image3, ui_positions["rss_gathered"], True
                )

            if self.scan_options.helps:
                governor_data.helps = preprocess_and_ocr_number(
                    api, image3, ui_positions["alliance_helps"], True
                )

        # Just to check the progress, printing in cmd the result for each governor
        governor_data.flag_unknown()

        self.state_callback("Closing governor")
        if self.is_page_needed(3):
            self.adb_client.secure_adb_tap(
                tap_positions["close_info"]
            )  # close more info
            wait_random_range(self.timings["info_close"], self.max_random_delay)
        self.adb_client.secure_adb_tap(
            tap_positions["close_gov"]
        )  # close governor info
        wait_random_range(self.timings["gov_close"], self.max_random_delay)

        end_time = time.time()

        self.output_handler("Time needed for governor: " + str((end_time - start_time)))
        self.scan_times.append(end_time - start_time)

        return governor_data

    # ------------------------------------------------------------------
    # City Hall verification methods
    # ------------------------------------------------------------------

    def _entry_to_gov_data(self, entry: dict) -> GovernorData:
        def de_intify(val):
            if val == -1: return "Unknown"
            if val == -2: return "Skipped"
            return val

        return GovernorData(
            id=de_intify(entry.get("ID", "Skipped")),
            name=entry.get("Name", "Skipped"),
            power=de_intify(entry.get("Power", "Skipped")),
            killpoints=de_intify(entry.get("Killpoints", "Skipped")),
            dead=de_intify(entry.get("Deads", "Skipped")),
            t1_kills=de_intify(entry.get("T1 Kills", "Skipped")),
            t2_kills=de_intify(entry.get("T2 Kills", "Skipped")),
            t3_kills=de_intify(entry.get("T3 Kills", "Skipped")),
            t4_kills=de_intify(entry.get("T4 Kills", "Skipped")),
            t5_kills=de_intify(entry.get("T5 Kills", "Skipped")),
            ranged_points=de_intify(entry.get("Ranged", "Skipped")),
            rss_gathered=de_intify(entry.get("Rss Gathered", "Skipped")),
            rss_assistance=de_intify(entry.get("Rss Assistance", "Skipped")),
            helps=de_intify(entry.get("Helps", "Skipped")),
            alliance=entry.get("Alliance", "Skipped"),
            city_hall_level=entry.get("City Hall Level", "Not Checked")
        )

    def get_governors_needing_ch(
        self, data_list: list, min_power: int = 25_000_000
    ) -> List[GovernorData]:
        """Identify governors that need in-game CH verification.

        - Governors with power >= min_power are auto-assigned CH 25.
        - Returns governors with 0 < power < min_power and city_hall_level == "Not Checked".
        """
        needing_check = []
        for entry in data_list:
            gov_power = entry.get("Power", 0)
            gov_id = entry.get("ID", 0)
            current_ch = entry.get("City Hall Level", "Not Checked")

            if gov_power <= 0 or gov_id <= 0:
                continue

            if current_ch != "Not Checked":
                # Already set (e.g., from a resumed scan)
                continue

            if gov_power >= min_power:
                # Auto-assign CH 25 for high-power governors
                entry["City Hall Level"] = 25
            else:
                # Reconstruct full GovernorData so frontend card shows all info
                gov = self._entry_to_gov_data(entry)
                needing_check.append(gov)

        return needing_check

    def _navigate_to_search_screen(self, tap_positions: dict) -> None:
        """Navigate from the ranking list to the governor search screen."""
        if self._in_search_screen:
            return

        self.state_callback("Navigating to search screen")
        # Close any open panels
        self.adb_client.secure_adb_tap(tap_positions["back_button"])
        time.sleep(0.5)
        self.adb_client.secure_adb_tap(tap_positions["back_button"])
        time.sleep(0.5)

        # Open settings / search
        self.adb_client.secure_adb_tap(tap_positions["settings"])
        time.sleep(1.0)
        self.adb_client.secure_adb_tap(tap_positions["search_gov_button"])
        time.sleep(1.0)

        self._in_search_screen = True
        self._first_search = True  # Track first search to skip field clearing

    def check_city_hall_level(
        self, governor_id: str, tap_positions: dict
    ) -> int:
        """Look up a governor by ID and read their City Hall level.

        Uses template matching as the primary method with Tesseract OCR fallback.
        Returns the CH level (1-25) or 0 if identification fails.
        """
        # Navigate to search screen if not already there
        self._navigate_to_search_screen(tap_positions)

        # Clear previous ID (skip on first entry)
        if not self._first_search:
            # Tap the input field first
            self.adb_client.secure_adb_tap(tap_positions["id_input_field"])
            time.sleep(0.3)
            # Send DEL keys to clear the field (batched into single ADB call)
            self.adb_client.secure_adb_shell(
                "input keyevent " + " ".join(["67"] * 15)
            )
        else:
            # Tap input field on first search
            self.adb_client.secure_adb_tap(tap_positions["id_input_field"])
            time.sleep(0.3)
            self._first_search = False

        # Input governor ID
        self.adb_client.secure_adb_shell(f"input text {governor_id}")
        time.sleep(0.3)

        # Tap search button
        self.adb_client.secure_adb_tap(tap_positions["search_button"])

        # Retry loop with exponential backoff
        backoff_times = [1.0, 1.5, 2.25]
        ch_level = 0

        for attempt, wait_time in enumerate(backoff_times):
            time.sleep(wait_time)

            # Take screenshot and crop the CH level region (with padding)
            screenshot = self.adb_client.secure_adb_screencap()
            screenshot_cv2 = pil_to_cv2(screenshot)
            crop = cropToRegion(screenshot_cv2, rok_ui.ch_level_region_padded)

            # Try to identify CH level
            ch_level = self._ch_matcher.identify(crop)

            if 1 <= ch_level <= 25:
                logger.info(
                    f"CH level for governor {governor_id}: {ch_level} "
                    f"(attempt {attempt + 1})"
                )
                return ch_level

            logger.debug(
                f"CH identification attempt {attempt + 1} failed for governor {governor_id}"
            )

        # All attempts failed — save debug image
        try:
            debug_path = self.img_path / f"ch_level_region_{governor_id}.png"
            write_cv2_img(crop, debug_path, "png")
            logger.warning(
                f"Failed to identify CH level for governor {governor_id}. "
                f"Debug image saved to {debug_path}"
            )
        except Exception as e:
            logger.warning(f"Failed to save debug image: {e}")

        return 0

    def _run_ch_verification_pass(
        self, data_handler: PandasHandler, tap_positions: dict
    ) -> None:
        """Second pass: verify City Hall levels for governors that need it."""
        if not self.config.scan.check_cityhall:
            return
        if self.stop_scan:
            return

        self.state_callback("Starting CH verification")
        self.output_handler("Starting City Hall level verification pass...")

        min_power = self.config.scan.ch_auto_assign_power
        governors_needing_ch = self.get_governors_needing_ch(
            data_handler.data_list, min_power
        )

        if not governors_needing_ch:
            self.output_handler("No governors need CH verification.")
            return

        self.output_handler(
            f"Verifying CH level for {len(governors_needing_ch)} governors..."
        )

        for i, gov in enumerate(governors_needing_ch):
            if self.stop_scan:
                self.output_handler("CH verification stopped.")
                break

            self.state_callback(
                f"Verifying CH: {i + 1}/{len(governors_needing_ch)}"
            )

            ch_level = self.check_city_hall_level(
                str(gov.id), tap_positions
            )

            if ch_level > 0:
                gov.city_hall_level = ch_level
                data_handler.update_governor(gov)
                data_handler.save()  # Incremental save for crash recovery

            # Emit progress callback
            self.gov_callback(
                gov,
                AdditionalData(
                    current_governor=i + 1,
                    target_governor=len(governors_needing_ch),
                    skipped_governors=0,
                    power_ok="Not Checked",
                    kills_ok="Not Checked",
                    reconstruction_success="Not Checked",
                    remaining_sec=0,
                    ch_verification_mode=True,
                    ch_current_governor=i + 1,
                    ch_total_governors=len(governors_needing_ch),
                ),
            )

        # Clean up: exit search screen
        if self._in_search_screen:
            self.adb_client.secure_adb_tap(tap_positions["back_button"])
            time.sleep(0.5)
            self.adb_client.secure_adb_tap(tap_positions["back_button"])
            self._in_search_screen = False

        data_handler.save()
        self.output_handler("CH verification pass complete.")

    def start_scan(
        self,
        kingdom: str,
        amount: int,
        resume: bool,
        track_inactives: bool,
        validate_kills: bool,
        reconstruct_fails: bool,
        validate_power: bool,
        power_threshold: int,
        formats: OutputFormats,
    ):
        self.state_callback("Initializing")
        self.adb_client.start_adb()
        if track_inactives:
            self.inactive_path.mkdir(parents=True, exist_ok=True)

        ######Excel Formatting
        # Resume Scan options. Refine the loop
        j = 0
        if resume:
            j = 4
            amount = amount + j

        if resume:
            file_name_prefix = "NEXT"
        else:
            file_name_prefix = "TOP"

        filename = f"{file_name_prefix}{amount - j}-{self.start_date}-{kingdom}-[{self.run_id}]"
        data_handler = PandasHandler(self.scan_path, filename, formats)

        # The loop in TOP XXX Governors in kingdom - It works both for power and killpoints Rankings
        # MUST have the tab opened to the 1st governor(Power or Killpoints)

        last_two = False
        next_gov_to_scan = -1
        last_gov_power = -1

        for i in range(j, amount):
            if self.stop_scan:
                self.output_handler("Scan Terminated! Saving the current progress...")
                break

            next_gov_to_scan = max(next_gov_to_scan + 1, i)
            gov_data = self.scan_governor(
                next_gov_to_scan,
                track_inactives,
            )

            # Check for duplicate governor
            if data_handler.is_duplicate(to_int_check(gov_data.id)):
                roi = (196, 698, 52, 27)
                image = pil_to_cv2(self.adb_client.secure_adb_screencap())

                im_ranking = cropToRegion(image, roi)
                im_ranking_bw = preprocessImage(im_ranking, 3, 90, 12, True)

                ranking = ""

                self._tess_api.SetPageSegMode(PSM.SINGLE_WORD)
                self._tess_api.SetImage(Image.fromarray(im_ranking_bw))  # type: ignore
                ranking = self._tess_api.GetUTF8Text()
                ranking = re.sub("[^0-9]", "", ranking)

                if ranking == "" or to_int_check(ranking) != 999:
                    self.output_handler(
                        f"Duplicate governor detected, but current rank is {ranking}, trying a second time."
                    )
                    logging.log(
                        logging.INFO,
                        f"Duplicate governor detected, but current rank is {ranking}, trying a second time.",
                    )

                    # repeat scan with next governor
                    gov_data = self.scan_governor(next_gov_to_scan, track_inactives)
                else:
                    if not last_two:
                        last_two = True
                        next_gov_to_scan = 998
                        self.output_handler(
                            "Duplicate governor detected, switching to scanning of last two governors."
                        )
                        logging.log(
                            logging.INFO,
                            "Duplicate governor detected, switching to scanning of last two governors.",
                        )

                        # repeat scan with next governor
                        gov_data = self.scan_governor(next_gov_to_scan, track_inactives)
                    else:
                        self.output_handler(
                            "Reached final governor on the screen. Scan complete."
                        )
                        logging.log(
                            logging.INFO,
                            "Reached final governor on the screen. Scan complete.",
                        )
                        self.state_callback("Scan finished")
                        return

            now = datetime.datetime.now()
            current_time = now.strftime("%H:%M:%S")

            kills_ok = "Not Checked"
            reconstruction_success = "Not Checked"
            if validate_kills:
                kills_ok = gov_data.validate_kills()
                if not kills_ok and reconstruct_fails:
                    reconstruction_success = gov_data.reconstruct_kills()

                    if reconstruction_success:
                        self.save_failed("kills", gov_data, True)
                    else:
                        self.save_failed("kills", gov_data, False)

            power_ok = "Not Checked"
            if validate_power:
                # TODO: Respect threshold here
                gov_power = to_int_check(gov_data.power)
                if gov_power == 0:
                    gov_power = -1

                power_ok = (gov_power != -1) and (
                    (last_gov_power == -1)
                    or (to_int_check(gov_data.power) < last_gov_power)
                )

                if power_ok:
                    last_gov_power = gov_power
                else:
                    self.save_failed("power", gov_data)

            if self.config.scan.check_cityhall:
                gov_power = to_int_check(gov_data.power)
                if gov_power != -1 and gov_power < self.config.scan.ch_auto_assign_power:
                    gov_data.city_hall_level = "Not Checked"
                elif gov_power != -1:
                    gov_data.city_hall_level = 25

            # Write results (batch save every 10 governors for performance)
            data_handler.write_governor(gov_data)
            if (i + 1) % 10 == 0 or self.stop_scan:
                data_handler.save()

            avg_time = (sum(self.scan_times) / len(self.scan_times)) if self.scan_times else 0.0
            speed_per_hour = (3600.0 / avg_time) if avg_time > 0 else 0.0
            elapsed = time.time() - self.scan_start_time

            additional_info = AdditionalData(
                current_governor=i + 1,
                target_governor=amount,
                skipped_governors=self.inactive_players,
                power_ok=str(power_ok),
                kills_ok=str(kills_ok),
                reconstruction_success=str(reconstruction_success),
                remaining_sec=self.get_remaining_time(amount - i),
                avg_time_per_governor=round(avg_time, 2),
                scan_speed_per_hour=round(speed_per_hour, 1),
                elapsed_sec=round(elapsed, 1),
            )

            self.gov_callback(gov_data, additional_info)

        data_handler.save()
        self.output_handler("Reached the target amount of people. Scan complete.")
        logging.log(logging.INFO, "Reached the target amount of people. Scan complete.")

        # --- City Hall verification second pass ---
        self._run_ch_verification_pass(data_handler, rok_ui.tap_positions)

        self.adb_client.kill_adb()  # make sure to clean up adb server
        self.cleanup()
        self.state_callback("Scan finished")
        return

    def cleanup(self):
        """Release persistent resources."""
        try:
            self._tess_api.End()
        except Exception:
            pass

    def end_scan(self):
        self.stop_scan = True